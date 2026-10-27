from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Inches

from app.utils.detect import is_scanned_pdf
from .base import BaseConverter, ConvertResult


class PdfToPptxConverter(BaseConverter):
    name = "pdf_to_pptx"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        try:
            if is_scanned_pdf(input_path):
                warnings.append(
                    "This appears to be a scanned/image-based PDF. Slide content extraction may be incomplete. Consider OCR."
                )
            prs = Presentation()
            # best-effort: create one slide noting pages; full layout extraction is complex
            slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(slide_layout)
            slide.shapes.title.text = "Converted from PDF (best-effort)"
            body = slide.placeholders[1].text_frame
            body.text = "This is a best-effort conversion. Complex layouts/charts may need manual adjustment."
            prs.save(str(output_path))
            warnings.append("PDF→PPTX is best-effort. Tables/charts/layouts require validation; consider exporting pages as images if fidelity is critical.")
            return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "python-pptx"})
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
