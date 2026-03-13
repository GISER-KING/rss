from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader


def load_pdf_chunks(
    pdf_path: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    基于滑动窗口的PDF文本语义提取

    Args:
        pdf_path: PDF文件路径
        chunk_size: 分块大小(字符数)，默认500
        chunk_overlap: 相邻块重叠字符数，默认50

    Returns:
        文本块列表，每个块包含text和metadata
    """
    p = Path(pdf_path)
    reader = PdfReader(pdf_path)
    docs: List[Dict[str, Any]] = []
    chunk_index = 0

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if not text.strip():
            continue

        # 滑动窗口分块
        if len(text) <= chunk_size:
            # 页面文本短于chunk_size，整页作为一个chunk
            docs.append({
                "text": text.strip(),
                "metadata": {
                    "file_name": p.name,
                    "page": page_num + 1,
                    "chunk_index": chunk_index,
                    "source": p.as_posix(),
                },
            })
            chunk_index += 1
        else:
            # 滑动窗口切分
            step = chunk_size - chunk_overlap
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end].strip()
                if chunk_text:
                    docs.append({
                        "text": chunk_text,
                        "metadata": {
                            "file_name": p.name,
                            "page": page_num + 1,
                            "chunk_index": chunk_index,
                            "source": p.as_posix(),
                        },
                    })
                    chunk_index += 1
                if end >= len(text):
                    break
                start += step

    return docs
