from pathlib import Path
from typing import Any

from pdf2docx import Converter

from app.utils.detect import is_scanned_pdf
from .base import BaseConverter, ConvertResult


class PdfToDocxConverter(BaseConverter):
    name = "pdf_to_docx"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        try:
            if is_scanned_pdf(input_path):
                warnings.append(
                    "This appears to be a scanned/image-based PDF. Text/layout extraction may be incomplete. "
                    "Consider OCR before converting to DOCX."
                )
            cv = Converter(str(input_path))
            cv.convert(str(output_path), start=0, end=None)
            cv.close()
            warnings.append("Complex layouts, tables, or unusual fonts may need manual correction.")
            return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "pdf2docx"})
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
