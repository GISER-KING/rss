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
from ..core.config import LANCEDB_DIR, UPLOADS_DIR, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DATA_DIR, API_TIMEOUT, API_MAX_RETRIES, API_RETRY_DELAY
from ..core.db import get_session
from sqlmodel import select
from ..db.models import DocumentRegistry, ShorelineResult
from ..utils.pdf import load_pdf_chunks
from datetime import datetime
from .dual_rag import DualStreamKnowledgeBase

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
    """构建传统单流知识库（保留用于兼容）"""
    if embedder is None:
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


def build_dual_stream_kb(embedder: LocalFastEmbedEmbedder | None = None) -> DualStreamKnowledgeBase:
    """构建双流RAG知识库（文档流+数据流）"""
    if embedder is None:
        models_dir = (DATA_DIR / "models").as_posix()
        os.makedirs(models_dir, exist_ok=True)
        print(f"Using local model cache: {models_dir}")
        embedder = LocalFastEmbedEmbedder(
            id="BAAI/bge-small-zh-v1.5",
            dimensions=512,
            cache_dir=models_dir
        )

    vector_db = LanceDb(
        table_name="dual_stream_kb",
        uri=os.path.abspath(LANCEDB_DIR.as_posix()),
        embedder=embedder,
    )

    dual_kb = DualStreamKnowledgeBase(vector_db=vector_db.connection, embedder=embedder)
    return dual_kb


from ..tools.water import extract_water_body
from ..tools.shoreline import classify_shoreline, query_shoreline_database, calculate_statistics
from .solution_space import SolutionDatabase
from .prompts import HierarchicalPromptEngine

def build_agent(api_base_url: str | None, api_key: str | None, mode: str = "chat") -> Agent:
    from ..core.config import API_BASE_URL, API_KEY, MODEL_ID

    # Prefer provided args, fallback to env vars
    base_url = api_base_url or API_BASE_URL
    key = api_key or API_KEY
    model_id = MODEL_ID

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
        role_map=role_map,
        temperature=0.7,
        top_p=0.9,
        max_tokens=2048,
        timeout=API_TIMEOUT,
        max_retries=API_MAX_RETRIES,
    )
    
    # Initialize Knowledge Base
    # We use a default embedder here. In a real scenario, we might want to configure this.
    # If using DeepSeek, we might need a separate OpenAI Key for embeddings or use a local one.
    kb = build_kb()
    
    # memory = SQLiteSessionMemory(namespace="river_shoreline")
    
    agent_tools = []
    if mode == "agent":
        # Enable tools only in agent mode
        agent_tools = [
            extract_water_body,
            classify_shoreline,
            query_shoreline_database,
            calculate_statistics
        ]
    else:
        # Chat mode - no tools or basic tools
        agent_tools = []

    # 使用层次化提示系统
    system_instructions = [
        HierarchicalPromptEngine.get_system_prompt(),
        "When a tool returns an image path or URL (e.g., in 'overlay_image'), you MUST display it using Markdown image syntax: ![Result Image](<url>).",
        "Do not just say 'the image is ready', show it.",
        "If the user uploads an image, use the provided path to call relevant tools."
    ]

    agent = Agent(
        name="RiverShorelineAgent",
        description="河流岸线空间智能感知系统",
        model=model,
        knowledge=kb,
        tools=agent_tools,
        markdown=True,
        search_knowledge=True,
        instructions=system_instructions
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


def _get_shared_embedder() -> LocalFastEmbedEmbedder:
    """获取共享的嵌入模型实例"""
    models_dir = (DATA_DIR / "models").as_posix()
    os.makedirs(models_dir, exist_ok=True)
    return LocalFastEmbedEmbedder(
        id="BAAI/bge-small-zh-v1.5",
        dimensions=512,
        cache_dir=models_dir
    )


def build_enhanced_agent(
    api_base_url: str | None,
    api_key: str | None,
    mode: str = "chat"
) -> tuple:
    """
    构建增强型Agent（双流RAG + 任务感知 + 层次化提示）

    Returns:
        (agent, dual_kb, solution_db) 三元组
    """
    from ..core.config import API_BASE_URL, API_KEY, MODEL_ID

    base_url = api_base_url or API_BASE_URL
    key = api_key or API_KEY
    model_id = MODEL_ID

    print(f"[Enhanced Agent] Model: {model_id}, Base URL: {base_url}")

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
        role_map=role_map,
        temperature=0.7,
        top_p=0.9,
        max_tokens=2048,
        timeout=API_TIMEOUT,
        max_retries=API_MAX_RETRIES,
    )

    # 共享嵌入模型
    embedder = _get_shared_embedder()

    # 构建双流知识库
    dual_kb = build_dual_stream_kb(embedder)

    # 构建解决方案数据库（使用语义相似度匹配）
    solution_db = SolutionDatabase(embedder=embedder)

    # 工具集
    agent_tools = []
    if mode == "agent":
        agent_tools = [
            extract_water_body,
            classify_shoreline,
            query_shoreline_database,
            calculate_statistics
        ]

    # 系统提示词（第1层：角色定位）
    system_instructions = [
        HierarchicalPromptEngine.get_system_prompt(),
        "When a tool returns an image path or URL (e.g., in 'overlay_image'), you MUST display it using Markdown image syntax: ![Result Image](<url>).",
        "Do not just say 'the image is ready', show it.",
        "If the user uploads an image, use the provided path to call relevant tools."
    ]

    agent = Agent(
        name="RiverShorelineAgent",
        description="河流岸线空间智能感知系统",
        model=model,
        tools=agent_tools,
        markdown=True,
        search_knowledge=False,  # 我们手动执行双流检索
        instructions=system_instructions
    )

    return agent, dual_kb, solution_db


def enhanced_stream_agent(
    agent: Agent,
    dual_kb: DualStreamKnowledgeBase,
    solution_db: SolutionDatabase,
    prompt: str,
    session_id: str
) -> Generator[Dict[str, Any], None, None]:
    """
    增强型流式Agent运行（论文核心流程）

    流程：
    1. 任务分类 → 方案检索（SolutionDatabase）
    2. 双流知识检索（hybrid_retrieval）
    3. 层次化提示构建
    4. Agent流式执行
    """
    from loguru import logger

    # ── Step 1: 任务分类（第2层提示） ──
    solution = solution_db.retrieve_solution(prompt)
    task_type = solution.get("task_type", "岸线知识问答")
    logger.info(f"[Enhanced] 任务分类: {task_type}")

    # 使用层次化提示引擎的任务分类提示（记录分类依据）
    classification_prompt = HierarchicalPromptEngine.get_task_classification_prompt(prompt)
    logger.debug(f"[Enhanced] 任务分类提示已生成")

    # ── Step 2: 双流知识检索 ──
    retrieval_results = []
    try:
        retrieval_results = dual_kb.hybrid_retrieval(prompt, top_k=5)
        logger.info(f"[Enhanced] 检索到 {len(retrieval_results)} 条结果")
    except Exception as e:
        logger.warning(f"[Enhanced] 双流检索失败（知识库可能为空）: {e}")

    # ── Step 3: 层次化提示构建 ──
    # 3a. 知识上下文
    knowledge_context = ""
    if retrieval_results:
        knowledge_parts = []
        for i, r in enumerate(retrieval_results, 1):
            source = r.get("stream_source", "未知")
            text = r.get("text", "")
            score = r.get("weighted_score", 0)
            knowledge_parts.append(f"[{source} #{i} 相关度:{score:.2f}]\n{text}")
        knowledge_context = "\n\n".join(knowledge_parts)

    # 3b. 方案指导
    solution_guidance = (
        f"任务类型: {task_type}\n"
        f"推荐工具: {', '.join(solution.get('required_tools', []))}\n"
        f"执行步骤:\n" + "\n".join(solution.get("execution_steps", []))
    )

    # 3c. 获取知识库统计（用于任务规划提示）
    try:
        kb_stats = dual_kb.get_statistics()
        doc_count = kb_stats.get("document_stream", {}).get("count", 0)
        data_count = kb_stats.get("data_stream", {}).get("count", 0)
    except Exception:
        doc_count, data_count = 0, 0

    # 3d. 使用层次化提示引擎构建各层prompt
    available_tools = ", ".join(solution.get("required_tools", [])) or "无（纯知识检索）"

    # 第3层：任务规划提示
    planning_prompt = HierarchicalPromptEngine.get_task_planning_prompt(
        task_type=task_type,
        solution_guidance=solution_guidance,
        query=prompt,
        available_tools=available_tools,
        doc_count=doc_count,
        data_count=data_count,
    )

    # 第4层：结果综合提示
    synthesis_prompt = HierarchicalPromptEngine.get_result_synthesis_prompt(
        query=prompt,
        tool_results="（工具执行结果将在运行后填充）",
        knowledge_results=knowledge_context or "（未检索到相关知识）",
    )

    # 组装最终增强prompt
    enhanced_prompt_parts = []

    # 注入任务分类结果（第2层）
    enhanced_prompt_parts.append(classification_prompt)
    enhanced_prompt_parts.append(f"系统判定结果：任务类型=「{task_type}」")

    # 注入任务规划（第3层）
    enhanced_prompt_parts.append(planning_prompt)

    # 注入检索到的知识（RAG上下文）
    if knowledge_context:
        enhanced_prompt_parts.append(
            f"【参考资料】以下是从知识库中检索到的相关信息，请基于这些信息回答问题：\n\n{knowledge_context}"
        )

    # 注入结果综合要求（第4层）
    enhanced_prompt_parts.append(synthesis_prompt)

    # 最后附上用户原始查询
    enhanced_prompt_parts.append(f"【用户查询】{prompt}")

    final_prompt = "\n\n".join(enhanced_prompt_parts)

    # ── Step 4: 流式执行（带重试机制） ──
    max_retries = API_MAX_RETRIES
    retry_count = 0
    references_sent = False

    while retry_count < max_retries:
        try:
            for chunk in agent.run(final_prompt, stream=True, session_id=session_id):
                data = {}
                if hasattr(chunk, "content"):
                    data["content"] = chunk.content

                    # 首次有内容时，随流发送检索引用
                    if not references_sent and retrieval_results:
                        references_sent = True
                        refs = []
                        seen_sources = set()
                        for r in retrieval_results:
                            metadata = r.get("metadata", {})
                            source_key = metadata.get("file_name") or metadata.get("region") or r.get("id", "")
                            if source_key and source_key in seen_sources:
                                continue
                            if source_key:
                                seen_sources.add(source_key)
                            refs.append({
                                "content": r.get("text", ""),
                                "meta_data": {
                                    "file_name": metadata.get("file_name") or metadata.get("source", ""),
                                    "page": metadata.get("page"),
                                    "region": metadata.get("region"),
                                    "stream_type": metadata.get("stream_type", "document"),
                                    "score": r.get("weighted_score", 0),
                                }
                            })
                        if refs:
                            data["references"] = refs

                    # 也处理Agno自带的引用（如果有）
                    if hasattr(chunk, "references") and chunk.references:
                        flattened_docs = []
                        for ref_obj in chunk.references:
                            if hasattr(ref_obj, "references") and isinstance(ref_obj.references, list):
                                flattened_docs.extend(ref_obj.references)
                            else:
                                flattened_docs.append(ref_obj)
                        serialized_refs = []
                        for doc in flattened_docs:
                            if hasattr(doc, "to_dict"):
                                serialized_refs.append(doc.to_dict())
                            elif hasattr(doc, "__dict__"):
                                serialized_refs.append(doc.__dict__)
                            else:
                                serialized_refs.append(str(doc))
                        if serialized_refs:
                            existing = data.get("references", [])
                            data["references"] = existing + serialized_refs

                elif isinstance(chunk, str):
                    data["content"] = chunk
                else:
                    try:
                        data["content"] = str(chunk)
                    except:
                        pass

                if data:
                    yield data

            # 如果成功完成，跳出重试循环
            break

        except Exception as e:
            retry_count += 1
            error_msg = str(e)
            logger.error(f"[Enhanced] Agent执行失败 (尝试 {retry_count}/{max_retries}): {error_msg}")

            # 判断是否为可重试的错误
            is_retryable = (
                "timeout" in error_msg.lower() or
                "timed out" in error_msg.lower() or
                "connection" in error_msg.lower() or
                "connection error" in error_msg.lower() or
                "network" in error_msg.lower()
            )

            # 判断是否为不可重试的错误（如免费额度耗尽）
            is_non_retryable = (
                "free tier" in error_msg.lower() or
                "quota" in error_msg.lower() or
                "exhausted" in error_msg.lower()
            )

            if is_non_retryable:
                # 不可重试的错误，直接返回错误信息
                logger.error(f"[Enhanced] 检测到不可重试错误: {error_msg}")
                yield {
                    "content": f"\n\n⚠️ 抱歉，处理请求时遇到问题: {error_msg}\n\n"
                }
                break
            elif is_retryable:
                if retry_count < max_retries:
                    logger.info(f"[Enhanced] 检测到可重试错误（{error_msg}），{API_RETRY_DELAY}秒后重试...")
                    import time
                    time.sleep(API_RETRY_DELAY)
                    continue
                else:
                    # 超过最大重试次数，返回错误信息和已检索的知识
                    yield {
                        "content": f"\n\n⚠️ API请求失败，已重试{max_retries}次仍失败。\n\n基于检索到的知识，这里是相关信息：\n\n",
                    }
                    if retrieval_results:
                        for i, r in enumerate(retrieval_results[:3], 1):
                            yield {
                                "content": f"**参考资料 {i}**（来源：{r.get('metadata', {}).get('file_name', '未知')}）\n{r.get('text', '')[:500]}...\n\n"
                            }
                    break
            else:
                # 其他未知错误，直接抛出
                raise


def ingest_shoreline_results(dual_kb: DualStreamKnowledgeBase, json_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    摄取岸线识别结果到数据流

    Args:
        dual_kb: 双流知识库实例
        json_data: 岸线识别结果JSON数据列表

    Returns:
        摄取统计信息
    """
    try:
        # 1. 存储到数据库
        with get_session() as s:
            for item in json_data:
                shoreline = ShorelineResult(
                    region=item.get("region", ""),
                    shoreline_type=item.get("shoreline_type", ""),
                    length_km=item.get("length_km", 0.0),
                    confidence=item.get("confidence", 0.0),
                    percentage=item.get("percentage"),
                    source_chapter=item.get("source_chapter", ""),
                    description=item.get("description"),
                    raw_data=str(item)
                )
                s.add(shoreline)
            s.commit()

        # 2. 索引到向量数据库
        count = dual_kb.ingest_data_stream(json_data)

        return {
            "success": True,
            "ingested": count,
            "message": f"成功摄取{count}条岸线数据"
        }
    except Exception as e:
        return {
            "success": False,
            "ingested": 0,
            "message": f"摄取失败: {str(e)}"
        }

