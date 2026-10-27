import os
from pathlib import Path
from typing import Any

from .base import BaseConverter, ConvertResult


class Win32OfficeToPdfConverter(BaseConverter):
    name = "win32_office_to_pdf"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        try:
            import win32com.client

            ext = input_path.suffix.lower()
            if ext in {".docx", ".doc"}:
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(str(input_path.resolve()))
                doc.SaveAs(str(output_path.resolve()), FileFormat=17)  # wdFormatPDF
                doc.Close()
                word.Quit()
            elif ext in {".xlsx", ".xls"}:
                excel = win32com.client.Dispatch("Excel.Application")
                excel.Visible = False
                wb = excel.Workbooks.Open(str(input_path.resolve()))
                wb.ExportAsFixedFormat(0, str(output_path.resolve()))  # xlTypePDF
                wb.Close(False)
                excel.Quit()
            elif ext in {".pptx", ".ppt"}:
                ppt = win32com.client.Dispatch("PowerPoint.Application")
                ppt.Visible = 1
                pres = ppt.Presentations.Open(str(input_path.resolve()), WithWindow=False)
                pres.SaveAs(str(output_path.resolve()), 32)  # ppSaveAsPDF
                pres.Close()
                ppt.Quit()
            else:
                return ConvertResult(ok=False, error="Unsupported for Win32 conversion")
            warnings.append("Converted via Microsoft Office (Win32).")
            return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "win32com"})
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
