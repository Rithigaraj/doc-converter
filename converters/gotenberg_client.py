import os
from pathlib import Path
import httpx
from app.config import settings


class GotenbergConverter:
    @staticmethod
    def get_url() -> str:
        return (settings.gotenberg_url or os.getenv("GOTENBERG_URL") or "http://localhost:3000").rstrip("/")

    @classmethod
    def is_available(cls) -> bool:
        url = cls.get_url()
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{url}/health")
                return res.status_code == 200
        except Exception:
            return False

    @classmethod
    def available(cls) -> bool:
        return cls.is_available()

    @classmethod
    def convert_to_pdf(cls, input_path: Path, output_path: Path, timeout: float = 120.0) -> tuple[bool, str | None]:
        url = cls.get_url()
        endpoint = f"{url}/forms/libreoffice/convert"
        try:
            with open(input_path, "rb") as f:
                files = {"files": (input_path.name, f, "application/octet-stream")}
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(endpoint, files=files)
            if resp.status_code == 200 and resp.content:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(resp.content)
                if output_path.exists() and output_path.stat().st_size > 0:
                    return True, None
                return False, "Gotenberg produced an empty response file"
            return False, f"Gotenberg error ({resp.status_code}): {resp.text[:300]}"
        except httpx.ConnectError:
            return False, f"Could not connect to Gotenberg at {url}"
        except httpx.TimeoutException:
            return False, f"Gotenberg conversion timed out after {timeout} seconds"
        except Exception as e:
            return False, f"Gotenberg request error: {str(e)}"
