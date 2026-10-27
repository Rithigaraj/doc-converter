import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.config import settings
from .base import BaseConverter, ConvertResult
from .gotenberg_client import GotenbergConverter
from .win32_pdf import Win32OfficeToPdfConverter


class DocxToPdfConverter(BaseConverter):
    name = "docx_to_pdf"

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any] | None = None) -> ConvertResult:
        options = options or {}
        warnings = []
        # Try Win32 (Microsoft Office) first on Windows if available
        try:
            w = Win32OfficeToPdfConverter().convert(input_path, output_path, options)
            if w.ok:
                return w
        except Exception:
            pass
        # Try Gotenberg first (works for all users via service)
        if GotenbergConverter.available():
            try:
                if GotenbergConverter.convert_to_pdf(input_path, output_path):
                    warnings.append("Converted via Gotenberg (LibreOffice in container). Fonts/tables preserved where supported.")
                    return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "gotenberg"})
            except Exception:
                pass
        soffice = settings.office_path
        if not shutil.which(soffice) and os.name == "nt":
            candidates = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            for c in candidates:
                if Path(c).exists():
                    soffice = c
                    break
        try:
            outdir = output_path.parent
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
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            if res.returncode != 0:
                return ConvertResult(ok=False, error=f"soffice failed: {res.stderr.decode(errors='ignore')[:500]}. Start Gotenberg (docker compose up gotenberg) or use Microsoft Office for server-side conversion.", warnings=warnings)
            produced = outdir / f"{input_path.stem}.pdf"
            if produced != output_path:
                if produced.exists():
                    produced.replace(output_path)
            if not output_path.exists():
                return ConvertResult(ok=False, error="PDF not produced by LibreOffice", warnings=warnings)
            warnings.append("Fonts/tables preserved where supported by LibreOffice.")
            return ConvertResult(ok=True, output_path=output_path, warnings=warnings, meta={"engine": "libreoffice"})
        except FileNotFoundError:
            return ConvertResult(ok=False, error="No conversion backend available. Install Microsoft Office, LibreOffice, or run Gotenberg (docker compose up gotenberg) for all users.", warnings=warnings)
        except subprocess.TimeoutExpired:
            return ConvertResult(ok=False, error="Conversion timed out", warnings=warnings)
        except Exception as e:
            return ConvertResult(ok=False, error=str(e), warnings=warnings)


