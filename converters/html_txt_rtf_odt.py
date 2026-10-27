from pathlib import Path
from typing import Any

import pypandoc

from .base import BaseConverter, ConvertResult


class HtmlTxtRtfOdtConverter(BaseConverter):
    name = "html_txt_rtf_odt"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        try:
            src = input_path.suffix.lower().lstrip(".")
            dst = output_path.suffix.lower().lstrip(".")
            # try pypandoc first
            try:
                pypandoc.convert_file(str(input_path), to=dst, outputfile=str(output_path))
                warnings.append("Converted via pypandoc where possible. Some styles may differ.")
                return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "pypandoc"})
            except Exception:
                pass
            # simple fallbacks
            if src in {"txt"} and dst == "docx":
                try:
                    from docx import Document

                    doc = Document()
                    text = input_path.read_text(encoding="utf-8", errors="ignore")
                    for para in text.splitlines():
                        doc.add_paragraph(para)
                    doc.save(str(output_path))
                    warnings.append("Simple text->DOCX conversion (minimal formatting).")
                    return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "python-docx-fallback"})
                except Exception as e:
                    return ConvertResult(ok=False, error=str(e))
            if src in {"html", "htm"} and dst == "pdf":
                try:
                    from weasyprint import HTML

                    HTML(filename=str(input_path)).write_pdf(str(output_path))
                    return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "weasyprint"})
                except Exception as e:
                    try:
                        from weasyhtml import HTML  # try old name

                        HTML(filename=str(input_path)).write_pdf(str(output_path))
                        return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "weasyhtml"})
                    except Exception:
                        return ConvertResult(ok=False, error=str(e))
            return ConvertResult(ok=False, error=f"Unsupported conversion {src}->{dst} in this build", warnings=warnings)
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
