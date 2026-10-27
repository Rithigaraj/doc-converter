import os
from pathlib import Path

import httpx

from app.config import settings


class GotenbergConverter:
    @staticmethod
    def available() -> bool:
        url = settings.gotenberg_url or os.getenv("GOTENBERG_URL")
        return bool(url)

    @staticmethod
    def convert_to_pdf(input_path: Path, output_path: Path) -> bool:
        url = settings.gotenberg_url or os.getenv("GOTENBERG_URL") or "http://localhost:3000"
        endpoint = f"{url.rstrip('/')}/forms/libreoffice/convert"
        try:
            with open(input_path, "rb") as f:
                files = {"files": (input_path.name, f, "application/octet-stream")}
                with httpx.Client(timeout=300) as client:
                    resp = client.post(endpoint, files=files)
            if resp.status_code == 200 and resp.content:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(resp.content)
                return output_path.exists()
            return False
        except Exception:
            return False
