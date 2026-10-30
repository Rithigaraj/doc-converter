import os
import subprocess
from pathlib import Path
from typing import Any

from app.config import settings, get_soffice_binary
from .base import BaseConverter, ConvertResult
from .gotenberg_client import GotenbergConverter
from .win32_pdf import Win32OfficeToPdfConverter


class DocxToPdfConverter(BaseConverter):
    name = "docx_to_pdf"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings: list[str] = []

        # 1. Try Gotenberg first (if configured/running)
        if GotenbergConverter.is_available():
            ok, err = GotenbergConverter.convert_to_pdf(input_path, output_path)
            if ok:
                warnings.append("Converted via Gotenberg (LibreOffice in container). Fonts/tables preserved where supported.")
                return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "gotenberg"})
            else:
                warnings.append(f"Gotenberg attempt failed: {err}. Falling back to local LibreOffice/Office.")

        # 2. Try local LibreOffice (soffice)
        soffice = get_soffice_binary()
        if soffice:
            try:
                outdir = output_path.parent
                outdir.mkdir(parents=True, exist_ok=True)
                cmd = [
                    soffice,
                    "--headless",
                    "--invisible",
                    "--nolockcheck",
                    "--nodefault",
                    "--nofirststartwizard",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(outdir),
                    str(input_path),
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
                if res.returncode == 0:
                    produced = outdir / f"{input_path.stem}.pdf"
                    if produced != output_path and produced.exists():
                        if output_path.exists():
                            output_path.unlink()
                        produced.replace(output_path)
                    if output_path.exists() and output_path.stat().st_size > 0:
                        warnings.append("Fonts/tables preserved where supported by LibreOffice.")
                        return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "libreoffice"})
                warnings.append(f"Local LibreOffice returned non-zero code {res.returncode}: {res.stderr.decode(errors='ignore')[:200]}")
            except subprocess.TimeoutExpired:
                warnings.append("Local LibreOffice conversion timed out.")
            except Exception as e:
                warnings.append(f"Local LibreOffice error: {str(e)}")

        # 3. On Windows, try MS Office via COM if available
        if os.name == "nt":
            try:
                w = Win32OfficeToPdfConverter().convert(input_path, output_path, options)
                if w.ok:
                    warnings.extend(w.warnings)
                    return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "win32com"})
            except Exception:
                pass

        error_msg = (
            "No Office-to-PDF conversion engine available. "
            "To convert DOCX/XLSX/PPTX/ODT/RTF to PDF, please either:\n"
            "1. Run Gotenberg via Docker: `docker compose up gotenberg` (or `docker run -p 3000:3000 gotenberg/gotenberg:8`)\n"
            "2. Install LibreOffice locally and ensure `soffice` is in your PATH\n"
            "3. Run the entire application via `docker compose up --build`"
        )
        return ConvertResult(ok=False, error=error_msg, warnings=warnings)
