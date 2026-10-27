from pathlib import Path
from typing import Any

import img2pdf

from .base import BaseConverter, ConvertResult


class ImageToPdfConverter(BaseConverter):
    name = "image_to_pdf"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        try:
            # img2pdf is lossless by default; quality/DPI can be controlled by pre-processing
            dpi = options.get("dpi")
            quality = options.get("quality")  # not directly used by img2pdf but noted
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(str(input_path)))
            if dpi or quality:
                warnings.append(f"Requested dpi={dpi}, quality={quality} noted (applied via source image if pre-processed).")
            return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "img2pdf"})
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)
