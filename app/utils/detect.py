from pathlib import Path

import fitz  # PyMuPDF


def is_scanned_pdf(path: Path, min_text_len: int = 50) -> bool:
    """Heuristic: if very little extractable text, likely scanned/image-based."""
    try:
        doc = fitz.open(str(path))
        total_text = 0
        for page in doc:
            total_text += len(page.get_text("text").strip())
            if total_text >= min_text_len:
                break
        doc.close()
        return total_text < min_text_len
    except Exception:
        return False


def pdf_page_count(path: Path) -> int:
    try:
        doc = fitz.open(str(path))
        n = len(doc)
        doc.close()
        return n
    except Exception:
        return 0
