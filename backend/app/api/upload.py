from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from pathlib import Path
from ..core.config import UPLOADS_DIR, DATA_DIR
from sqlmodel import select
from ..core.db import get_session
from ..db.models import DocumentRegistry
from ..agents.river_agent import build_kb, build_dual_stream_kb, ingest_uploads
from datetime import datetime

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

        # 1. 摄取到单流知识库（兼容Agno的内置搜索）
        kb = build_kb()
        result = ingest_uploads(kb)

        # 2. 同时摄取到双流知识库的文档流
        dual_kb = build_dual_stream_kb()
        dual_count = 0
        try:
            dual_count = dual_kb.ingest_document_stream(file_path.as_posix())
        except Exception as e:
            print(f"双流文档流摄取失败（非致命）: {e}")

        # 3. 更新DocumentRegistry
        with get_session() as s:
            existing = s.exec(
                select(DocumentRegistry).where(DocumentRegistry.filename == file.filename)
            ).first()
            if not existing:
                doc_reg = DocumentRegistry(
                    filename=file.filename,
                    file_path=file_path.as_posix(),
                    ingested=True,
                    ingested_at=datetime.utcnow(),
                )
                s.add(doc_reg)
                s.commit()

        return {
            "filename": file.filename,
            "ingested": True,
            "details": result,
            "dual_stream_chunks": dual_count,
        }

    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image")
async def upload_image(user_id: int, file: UploadFile = File(...)):
    """上传遥感影像文件"""
    allowed_ext = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
    if not file.filename.lower().endswith(allowed_ext):
        raise HTTPException(status_code=400, detail=f"Supported formats: {', '.join(allowed_ext)}")

    upload_dir = DATA_DIR / "uploads" / "images"
    os.makedirs(upload_dir.as_posix(), exist_ok=True)
    file_path = upload_dir / file.filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "file_path": file_path.as_posix(),
            "file_name": file.filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
