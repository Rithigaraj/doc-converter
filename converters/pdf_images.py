from pathlib import Path
from typing import Any

from pdf2image import convert_from_path

from app.config import settings
from .base import BaseConverter, ConvertResult


class PdfToImagesConverter(BaseConverter):
    name = "pdf_to_images"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        try:
            dpi = int(options.get("dpi", 200))
            fmt = options.get("format", "png").lower()  # png/jpeg
            if fmt not in {"png", "jpg", "jpeg"}:
                fmt = "png"
            poppler_path = settings.poppler_path or None
            pages = convert_from_path(str(input_path), dpi=dpi, poppler_path=poppler_path)
            # output_path is base; we save multiple files next to it or as zip? but converter returns single path
            # easier: save as first page or create a zip of images - but API expects single output; handle in worker
            outdir = output_path.parent
            stem = output_path.stem
            saved = []
            for i, page in enumerate(pages):
                p = outdir / f"{stem}_page_{i + 1}.{fmt if fmt != 'jpg' else 'jpg'}"
                if fmt in {"jpg", "jpeg"}:
                    page.save(p, "JPEG", quality=int(options.get("quality", 90)))
                else:
                    page.save(p, "PNG")
                saved.append(p)
            # if multiple, worker can zip; return first as representative? better: write a marker
            warnings.append(f"Saved {len(saved)} image(s) at {dpi} DPI. If multiple pages, results may be packaged as ZIP by the service.")
            # return first path but note - API/worker will handle multi
            return ConvertResult(ok=True, output_path=saved[0] if saved else output_path, warnings=warnings, meta={"images": [str(s) for s in saved], "engine": "pdf2image"})
        except FileNotFoundError:
            return ConvertResult(ok=False, error="Poppler not found. Install poppler and set POPPLER_PATH or add to PATH (required for pdf2image).", warnings=warnings)
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
