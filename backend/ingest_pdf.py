"""手动摄取uploads目录中的PDF文件到知识库"""
import sys
from pathlib import Path
from app.agents.river_agent import build_kb, build_dual_stream_kb, ingest_uploads
from app.core.config import UPLOADS_DIR
from app.core.db import get_session
from app.db.models import DocumentRegistry
from sqlmodel import select
from datetime import datetime

def main():
    print("=" * 60)
    print("开始摄取PDF文件到知识库")
    print("=" * 60)

    # 1. 检查uploads目录
    pdf_files = list(UPLOADS_DIR.glob("*.pdf"))
    print(f"\n找到 {len(pdf_files)} 个PDF文件:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")

    if not pdf_files:
        print("\n[ERROR] uploads目录中没有PDF文件")
        return

    # 2. 摄取到单流知识库
    print("\n" + "=" * 60)
    print("步骤1: 摄取到单流知识库 (riverai_kb)")
    print("=" * 60)
    try:
        kb = build_kb()
        result = ingest_uploads(kb)
        print(f"[OK] 单流知识库摄取完成: {result}")
    except Exception as e:
        print(f"[ERROR] 单流知识库摄取失败: {e}")

    # 3. 摄取到双流知识库的文档流
    print("\n" + "=" * 60)
    print("步骤2: 摄取到双流知识库 (dual_stream_kb)")
    print("=" * 60)
    try:
        dual_kb = build_dual_stream_kb()
        total_chunks = 0
        for pdf_file in pdf_files:
            print(f"\n处理: {pdf_file.name}")
            chunk_count = dual_kb.ingest_document_stream(pdf_file.as_posix())
            print(f"  [OK] 生成 {chunk_count} 个文本块")
            total_chunks += chunk_count

        print(f"\n[OK] 双流知识库摄取完成，共 {total_chunks} 个文本块")
    except Exception as e:
        print(f"[ERROR] 双流知识库摄取失败: {e}")
        import traceback
        traceback.print_exc()

    # 4. 更新DocumentRegistry
    print("\n" + "=" * 60)
    print("步骤3: 更新文档注册表")
    print("=" * 60)
    try:
        with get_session() as s:
            for pdf_file in pdf_files:
                existing = s.exec(
                    select(DocumentRegistry).where(
                        DocumentRegistry.filename == pdf_file.name
                    )
                ).first()

                if not existing:
                    doc_reg = DocumentRegistry(
                        filename=pdf_file.name,
                        file_path=pdf_file.as_posix(),
                        ingested=True,
                        ingested_at=datetime.utcnow(),
                    )
                    s.add(doc_reg)
                    print(f"  [OK] 注册: {pdf_file.name}")
                else:
                    existing.ingested = True
                    existing.ingested_at = datetime.utcnow()
                    print(f"  [OK] 更新: {pdf_file.name}")

            s.commit()
        print("\n[OK] 文档注册表更新完成")
    except Exception as e:
        print(f"[ERROR] 文档注册表更新失败: {e}")

    # 5. 验证结果
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    try:
        import lancedb
        db = lancedb.connect("data/lancedb")

        # 检查dual_stream_kb
        tbl = db.open_table("dual_stream_kb")
        count = tbl.count_rows()
        print(f"[OK] dual_stream_kb表记录数: {count}")

        if count > 0:
            print("\n[SUCCESS] PDF摄取成功！现在可以运行评估脚本了")
        else:
            print("\n[WARNING] dual_stream_kb表仍然为空，请检查错误信息")

    except Exception as e:
        print(f"[ERROR] 验证失败: {e}")

    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
