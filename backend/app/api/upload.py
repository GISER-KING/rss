from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from ..core.config import UPLOADS_DIR
from ..agents.river_agent import build_kb, ingest_uploads

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/pdf")
async def upload_pdf(user_id: int, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    os.makedirs(UPLOADS_DIR.as_posix(), exist_ok=True)
    file_path = UPLOADS_DIR / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Trigger ingestion
        kb = build_kb()
        result = ingest_uploads(kb)
        
        return {"filename": file.filename, "ingested": True, "details": result}
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
