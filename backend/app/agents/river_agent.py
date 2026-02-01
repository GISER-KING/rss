import os
from typing import Generator, Dict, Any, List
from agno.agent import Agent
from agno.models.openai import OpenAIChat
# from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.vectordb.lancedb import LanceDb
from agno.knowledge import Knowledge
from agno.knowledge.document import Document
from agno.knowledge.embedder.base import Embedder
from ..core.config import LANCEDB_DIR, UPLOADS_DIR, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DATA_DIR
from ..core.db import get_session
from sqlmodel import select
from ..db.models import DocumentRegistry
from ..utils.pdf import load_pdf_chunks
from datetime import datetime

# Define LocalFastEmbedEmbedder to support custom cache directory
class LocalFastEmbedEmbedder(Embedder):
    def __init__(self, id: str = "BAAI/bge-small-zh-v1.5", dimensions: int = 512, cache_dir: str = None):
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ImportError("fastembed not installed")
            
        self.id = id
        self.dimensions = dimensions
        self.cache_dir = cache_dir
        # Initialize model once
        self.model = TextEmbedding(model_name=id, cache_dir=cache_dir)
        
    def get_embedding(self, text: str) -> List[float]:
        embeddings = self.model.embed(text)
        # fastembed returns a generator of numpy arrays or lists
        return list(list(embeddings)[0])
        
    def get_embedding_and_usage(self, text: str):
        return self.get_embedding(text), None
        
    async def async_get_embedding(self, text: str) -> List[float]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_embedding, text)

def build_kb(embedder: LocalFastEmbedEmbedder | None = None) -> Knowledge:
    if embedder is None:
        # Use LocalFastEmbedEmbedder with specific cache directory
        models_dir = (DATA_DIR / "models").as_posix()
        os.makedirs(models_dir, exist_ok=True)
        print(f"Using local model cache: {models_dir}")
        embedder = LocalFastEmbedEmbedder(
            id="BAAI/bge-small-zh-v1.5", 
            dimensions=512,
            cache_dir=models_dir
        )
        
    vector_db = LanceDb(
        table_name="riverai_kb",
        uri=os.path.abspath(LANCEDB_DIR.as_posix()),
        embedder=embedder,
    )
    
    kb = Knowledge(vector_db=vector_db)
    return kb


from ..tools.water import extract_water_body

def build_agent(api_base_url: str | None, api_key: str | None, mode: str = "chat") -> Agent:
    # Prefer provided args, fallback to env vars
    base_url = api_base_url or DEEPSEEK_BASE_URL
    key = api_key or DEEPSEEK_API_KEY
    model_id = DEEPSEEK_MODEL

    print(f"Using Model: {model_id}, Base URL: {base_url}") # Debug log
    
    # Define role map to ensure "system" role is preserved for DeepSeek
    role_map = {
        "system": "system",
        "user": "user",
        "assistant": "assistant",
        "tool": "tool",
        "model": "assistant",
    }
    
    model = OpenAIChat(
        id=model_id, 
        base_url=base_url, 
        api_key=key,
        role_map=role_map
    )
    
    # Initialize Knowledge Base
    # We use a default embedder here. In a real scenario, we might want to configure this.
    # If using DeepSeek, we might need a separate OpenAI Key for embeddings or use a local one.
    kb = build_kb()
    
    # memory = SQLiteSessionMemory(namespace="river_shoreline")
    
    agent_tools = []
    if mode == "agent":
        # Enable tools only in agent mode
        agent_tools = [extract_water_body]
    else:
        # Chat mode - no tools or basic tools
        agent_tools = []

    agent = Agent(
        name="RiverShorelineAgent",
        description="河流岸线空间智能感知系统",
        model=model,
        knowledge=kb,
        tools=agent_tools,
        # function_calling=True, # DeepSeek V3 supports function calling
        markdown=True,
        # memory=memory,
        search_knowledge=True, # Enable searching knowledge base
        instructions=[
            "When a tool returns an image path or URL (e.g., in 'overlay_image'), you MUST display it using Markdown image syntax: ![Result Image](<url>).",
            "Do not just say 'the image is ready', show it.",
            "If the user uploads an image, use the provided path to call relevant tools."
        ]
    )
    return agent


def ingest_pdf_file(kb: Knowledge, pdf_path: str) -> Dict[str, Any]:
    raw_docs = load_pdf_chunks(pdf_path)
    if not raw_docs:
        return {"ingested": 0, "file": pdf_path}
    
    documents = [
        Document(content=d["text"], meta_data=d["metadata"]) 
        for d in raw_docs
    ]
    
    if hasattr(kb, 'load_documents'):
        kb.load_documents(documents=documents, upsert=True)
    elif hasattr(kb, 'load'):
        kb.load(documents=documents, recreate=False)
    else:
                         # Fallback for newer Agno versions where loading might be done differently
        # Attempting to use add_documents or similar if available, otherwise checking source
        try:
             # Try direct vector_db insertion if kb.load/load_documents missing
             if kb.vector_db:
                 import hashlib
                 content_hash = hashlib.md5(pdf_path.encode()).hexdigest()
                 
                 # Ensure we are calling the correct method for LanceDb
                 # Check if insert method exists
                 if hasattr(kb.vector_db, 'insert'):
                     kb.vector_db.insert(documents=documents)
                 elif hasattr(kb.vector_db, 'add_documents'):
                     kb.vector_db.add_documents(documents=documents)
                 elif hasattr(kb.vector_db, 'upsert'):
                     kb.vector_db.upsert(documents=documents)
                 else:
                     print("Warning: No suitable method found to insert documents into VectorDB")
                     
        except Exception as e:
            print(f"Error loading documents: {e}")
            raise
    return {"ingested": len(documents), "file": pdf_path}


def ingest_uploads(kb: Knowledge) -> Dict[str, Any]:
    os.makedirs(UPLOADS_DIR.as_posix(), exist_ok=True)
    
    # 1. Scan files
    files_on_disk = []
    for fn in os.listdir(UPLOADS_DIR):
        if fn.lower().endswith(".pdf"):
            files_on_disk.append(fn)
            
    total_chunks = 0
    new_files = []
    
    with get_session() as s:
        for fn in files_on_disk:
            file_path = (UPLOADS_DIR / fn).as_posix()
            
            # Check if already ingested
            existing = s.exec(select(DocumentRegistry).where(DocumentRegistry.filename == fn)).first()
            
            if existing and existing.ingested:
                print(f"Skipping already ingested file: {fn}")
                continue
                
            print(f"Ingesting new file: {fn}")
            
            # Create or update registry entry
            if not existing:
                doc_reg = DocumentRegistry(filename=fn, file_path=file_path)
                s.add(doc_reg)
                s.commit()
                s.refresh(doc_reg)
            else:
                doc_reg = existing

            try:
                # Ingest
                res = ingest_pdf_file(kb, file_path)
                
                # Update status
                doc_reg.ingested = True
                doc_reg.ingested_at = datetime.utcnow()
                s.add(doc_reg)
                s.commit()
                
                total_chunks += res["ingested"]
                new_files.append(fn)
                
            except Exception as e:
                print(f"Failed to ingest {fn}: {e}")
    
    return {"files": new_files, "chunks": total_chunks}


def stream_agent(agent: Agent, prompt: str, session_id: str) -> Generator[Dict[str, Any], None, None]:
    for chunk in agent.run(prompt, stream=True, session_id=session_id):
        # Handle RunContentEvent
        data = {}
        if hasattr(chunk, "content"):
             data["content"] = chunk.content
             if hasattr(chunk, "references") and chunk.references:
                 # Flatten references: Extract documents from MessageReferences
                 flattened_docs = []
                 for ref_obj in chunk.references:
                     # Check if it's a MessageReferences object (which has a 'references' list attribute)
                     if hasattr(ref_obj, "references") and isinstance(ref_obj.references, list):
                         flattened_docs.extend(ref_obj.references)
                     else:
                         # It might be a direct Document object or dict
                         flattened_docs.append(ref_obj)
                         
                 # Serialize the flattened list
                 serialized_refs = []
                 for doc in flattened_docs:
                     if hasattr(doc, "to_dict"):
                         serialized_refs.append(doc.to_dict())
                     elif hasattr(doc, "__dict__"):
                         serialized_refs.append(doc.__dict__)
                     else:
                         serialized_refs.append(str(doc))
                         
                 # Deduplicate references based on filename
                 seen_files = set()
                 unique_refs = []
                 for doc in serialized_refs:
                     # Try to get filename from meta_data or file_name attribute
                     file_name = None
                     if isinstance(doc, dict):
                         meta_data = doc.get('meta_data', {})
                         file_name = meta_data.get('file_name') or doc.get('file_name')
                     
                     if file_name:
                         if file_name not in seen_files:
                             seen_files.add(file_name)
                             unique_refs.append(doc)
                     else:
                         # If no filename, just add it (or decide to skip)
                         unique_refs.append(doc)
                 
                 data["references"] = unique_refs
                 # Debug log to verify references are being sent
                 print(f"DEBUG: Sending {len(unique_refs)} unique references in stream chunk")
                 
             if hasattr(chunk, "citations") and chunk.citations:
                 # Serialize citations to dict if they are objects
                 serialized_cits = []
                 for cit in chunk.citations:
                     if hasattr(cit, "to_dict"):
                         serialized_cits.append(cit.to_dict())
                     elif hasattr(cit, "__dict__"):
                         serialized_cits.append(cit.__dict__)
                     else:
                         serialized_cits.append(str(cit))
                 data["citations"] = serialized_cits
        elif isinstance(chunk, str):
            data["content"] = chunk
        else:
            # Check for specific agno types that might need string conversion
            try:
                data["content"] = str(chunk)
            except:
                pass
            
        if data:
            yield data

