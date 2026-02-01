from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader


def load_pdf_chunks(pdf_path: str) -> List[Dict[str, Any]]:
    p = Path(pdf_path)
    reader = PdfReader(pdf_path)
    docs: List[Dict[str, Any]] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        docs.append(
            {
                "text": text,
                "metadata": {"file_name": p.name, "page": i + 1, "source": p.as_posix()},
            }
        )
    return docs

