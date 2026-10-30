import io
from pathlib import Path
from typing import Any
from PIL import Image
import pymupdf

from app.config import settings
from .base import BaseConverter, ConvertResult


class PdfToImagesConverter(BaseConverter):
    name = "pdf_to_images"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings: list[str] = []
        try:
            dpi = int(options.get("dpi", 200))
            fmt = str(options.get("format", output_path.suffix.lstrip(".") or "png")).lower()
            if fmt not in {"png", "jpg", "jpeg"}:
                fmt = "png"
            quality = int(options.get("quality", 90))

            outdir = output_path.parent
            outdir.mkdir(parents=True, exist_ok=True)
            stem = output_path.stem
            saved_paths: list[Path] = []

            # Primary high-speed native engine: PyMuPDF (no external poppler binary required)
            doc = pymupdf.open(str(input_path))
            total_pages = len(doc)
            if total_pages == 0:
                doc.close()
                return ConvertResult(ok=False, error="PDF contains no pages", warnings=warnings)

            for i, page in enumerate(doc):
                img_ext = "jpg" if fmt in {"jpg", "jpeg"} else "png"
                img_path = outdir / f"{stem}_page_{i + 1}.{img_ext}"
                pix = page.get_pixmap(dpi=dpi)
                
                if fmt in {"jpg", "jpeg"}:
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    img.convert("RGB").save(str(img_path), "JPEG", quality=quality)
                else:
                    pix.save(str(img_path))
                saved_paths.append(img_path)
            doc.close()

            warnings.append(f"Rendered {len(saved_paths)} page(s) at {dpi} DPI ({fmt.upper()}).")
            if len(saved_paths) > 1:
                warnings.append("Multi-page document: results packaged into ZIP.")

            primary_output = saved_paths[0] if saved_paths else output_path
            return ConvertResult(
                ok=True,
                output_path=primary_output,
                warnings=warnings,
                meta={
                    "images": [str(p) for p in saved_paths],
                    "count": len(saved_paths),
                    "engine": "pymupdf",
                    "dpi": dpi,
                    "format": fmt,
                }
            )
        except Exception as e:
            return ConvertResult(ok=False, error=f"PDF to images conversion failed: {str(e)}", warnings=warnings)
