import io
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup
from docx import Document
from pptx import Presentation
import openpyxl
import pandas as pd
from PIL import Image
import pymupdf

from app.utils.detect import is_scanned_pdf


@dataclass
class ExtractedDocument:
    text: str
    filename: str
    page_count: int = 1
    is_ocr: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _try_ocr_image(img: Image.Image) -> str | None:
    """Attempt OCR on an image using pytesseract if available."""
    try:
        import pytesseract
        return pytesseract.image_to_string(img).strip()
    except Exception:
        return None


def extract_document_text(file_path: Path, filename: str | None = None) -> ExtractedDocument:
    """
    Extracts plain text across PDF, DOCX, PPTX, XLSX, CSV, HTML, TXT, RTF, ODT, and images.
    Detects scanned PDFs and applies OCR when needed/possible.
    """
    path = Path(file_path)
    fname = filename or path.name
    ext = path.suffix.lower().lstrip(".")
    warnings: list[str] = []
    is_ocr = False
    extracted_text = ""
    page_count = 1

    try:
        # 1. PDF Documents
        if ext == "pdf":
            doc = pymupdf.open(str(path))
            page_count = len(doc)
            pages_text: list[str] = []
            low_text_pages = 0

            for i, page in enumerate(doc):
                txt = page.get_text("text").strip()
                if len(txt) < 40:
                    low_text_pages += 1
                    # Attempt OCR on page image
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_result = _try_ocr_image(img)
                    if ocr_result and len(ocr_result) > len(txt):
                        txt = ocr_result
                        is_ocr = True
                pages_text.append(f"--- Page {i + 1} ---\n{txt}")

            doc.close()

            if is_scanned_pdf(path) or (page_count > 0 and low_text_pages / page_count > 0.6):
                if is_ocr:
                    warnings.append("Document appears to be scanned; optical character recognition (OCR) was applied.")
                else:
                    warnings.append("Document appears to be scanned or image-based. Text content may be limited without OCR engine.")

            extracted_text = "\n\n".join(pages_text).strip()

        # 2. Microsoft Word (DOCX)
        elif ext in {"docx", "doc"}:
            try:
                doc = Document(str(path))
                paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                tables_text = []
                for table in doc.tables:
                    for row in table.rows:
                        row_vals = [c.text.strip() for c in row.cells if c.text.strip()]
                        if row_vals:
                            tables_text.append(" | ".join(row_vals))
                all_parts = paras + (["--- Tables ---"] + tables_text if tables_text else [])
                extracted_text = "\n".join(all_parts)
                page_count = max(1, len(paras) // 5)
            except Exception as e:
                warnings.append(f"Word extraction notice: {str(e)}")

        # 3. Microsoft PowerPoint (PPTX)
        elif ext in {"pptx", "ppt"}:
            prs = Presentation(str(path))
            page_count = len(prs.slides)
            slides_text = []
            for idx, slide in enumerate(prs.slides, 1):
                slide_content = [f"--- Slide {idx} ---"]
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_content.append(shape.text.strip())
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                    if notes:
                        slide_content.append(f"[Speaker Notes]: {notes}")
                slides_text.append("\n".join(slide_content))
            extracted_text = "\n\n".join(slides_text)

        # 4. Tabular Data (XLSX, XLS, CSV)
        elif ext in {"xlsx", "xls"}:
            wb = openpyxl.load_workbook(str(path), data_only=True)
            sheets_text = []
            for sheetname in wb.sheetnames:
                ws = wb[sheetname]
                rows_text = [f"=== Sheet: {sheetname} ==="]
                for row in ws.iter_rows(values_only=True):
                    row_vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                    if row_vals:
                        rows_text.append(", ".join(row_vals))
                sheets_text.append("\n".join(rows_text))
            extracted_text = "\n\n".join(sheets_text)
            page_count = len(wb.sheetnames)

        elif ext == "csv":
            df = pd.read_csv(path, sep=None, engine='python')
            extracted_text = df.to_string(index=False)
            page_count = 1

        # 5. HTML Documents
        elif ext in {"html", "htm"}:
            raw = path.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            extracted_text = soup.get_text(separator="\n", strip=True)

        # 6. Plain Text / RTF / ODT
        elif ext == "txt":
            extracted_text = path.read_text(encoding="utf-8", errors="ignore")

        elif ext in {"rtf", "odt"}:
            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
                # Basic ASCII/text extraction from RTF
                lines = [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("{\\")]
                extracted_text = "\n".join(lines)
            except Exception:
                extracted_text = path.read_text(encoding="latin1", errors="ignore")

        # 7. Image Formats
        elif ext in {"png", "jpg", "jpeg", "tif", "tiff", "bmp", "gif"}:
            img = Image.open(path)
            ocr_text = _try_ocr_image(img)
            if ocr_text:
                extracted_text = ocr_text
                is_ocr = True
                warnings.append("Text extracted from image using Optical Character Recognition (OCR).")
            else:
                extracted_text = f"[Image file: {fname}, Dimensions: {img.width}x{img.height}px]"
                warnings.append("OCR was unable to extract legible text from this image.")

        else:
            extracted_text = path.read_text(encoding="utf-8", errors="ignore")

    except Exception as e:
        warnings.append(f"Error during document extraction: {str(e)}")

    return ExtractedDocument(
        text=extracted_text.strip(),
        filename=fname,
        page_count=max(1, page_count),
        is_ocr=is_ocr,
        warnings=warnings
    )
