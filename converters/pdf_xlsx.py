from pathlib import Path
from typing import Any

import pdfplumber

from app.utils.detect import is_scanned_pdf
from .base import BaseConverter, ConvertResult


class PdfToXlsxConverter(BaseConverter):
    name = "pdf_to_xlsx"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        try:
            if is_scanned_pdf(input_path):
                warnings.append(
                    "This appears to be a scanned/image-based PDF. Table extraction may be incomplete. Consider OCR."
                )
            with pdfplumber.open(str(input_path)) as pdf:
                tables = []
                for page in pdf.pages:
                    tables.extend(page.extract_tables() or [])
            if not tables:
                warnings.append("No tables detected by pdfplumber. Output may be limited or require manual extraction/validation.")
            # try to write simple xlsx
            try:
                import openpyxl

                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Sheet1"
                row = 1
                for t in tables:
                    for r in t:
                        for cidx, val in enumerate(r or []):
                            ws.cell(row=row, column=cidx + 1, value=val)
                        row += 1
                    row += 1  # blank line between tables
                wb.save(str(output_path))
            except Exception:
                # fallback minimal
                import pandas as pd

                all_rows = []
                for t in tables:
                    for r in t:
                        all_rows.append(r)
                df = pd.DataFrame(all_rows)
                df.to_excel(str(output_path), index=False)
            warnings.append("Complex tables/charts/layouts require validation. Best-effort extraction.")
            return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "pdfplumber"})
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
