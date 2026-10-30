import os
import shutil
import time
from pathlib import Path
from typing import Any
import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "Doc Converter"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Absolute storage paths
    upload_dir: Path = BASE_DIR / "uploads"
    output_dir: Path = BASE_DIR / "outputs"
    tmp_dir: Path = BASE_DIR / "tmp"

    max_upload_mb: int = 500
    purge_age_hours: int = 24

    redis_url: str = "redis://localhost:6379/0"
    rq_queue: str = "doc-jobs"

    office_path: str = "soffice"
    gotenberg_url: str | None = None
    poppler_path: str | None = None
    pandoc_path: str | None = None
    ghostscript_path: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"


settings = Settings()

# Ensure absolute paths
settings.upload_dir = Path(settings.upload_dir).resolve()
settings.output_dir = Path(settings.output_dir).resolve()
settings.tmp_dir = Path(settings.tmp_dir).resolve()

for directory in [settings.upload_dir, settings.output_dir, settings.tmp_dir]:
    directory.mkdir(parents=True, exist_ok=True)


def get_soffice_binary() -> str | None:
    """Find LibreOffice executable path."""
    configured = settings.office_path
    if shutil.which(configured):
        return configured
    if Path(configured).exists():
        return str(Path(configured).resolve())
    
    if os.name == "nt":
        candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
    return None


_last_tool_check = 0.0
_cached_tool_status: dict[str, Any] = {}


def detect_tool_status(force_refresh: bool = False) -> dict[str, Any]:
    """Detect presence and availability of external tools and services with 10s caching."""
    global _last_tool_check, _cached_tool_status
    now = time.time()
    if not force_refresh and _cached_tool_status and (now - _last_tool_check < 10.0):
        return _cached_tool_status

    soffice_bin = get_soffice_binary()
    
    # Check Gotenberg (with ultra-low timeout to prevent blocking)
    gotenberg_ok = False
    g_url = settings.gotenberg_url or os.getenv("GOTENBERG_URL") or "http://localhost:3000"
    try:
        with httpx.Client(timeout=0.4) as client:
            resp = client.get(f"{g_url.rstrip('/')}/health")
            gotenberg_ok = (resp.status_code == 200)
    except Exception:
        gotenberg_ok = False

    # Check Redis
    redis_ok = False
    try:
        import redis
        client = redis.from_url(settings.redis_url, socket_connect_timeout=0.3)
        client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    # Check Poppler
    poppler_ok = bool(shutil.which("pdftoppm") or (settings.poppler_path and Path(settings.poppler_path).exists()))

    # Check Pandoc
    pandoc_ok = bool(shutil.which("pandoc") or (settings.pandoc_path and Path(settings.pandoc_path).exists()))

    # Check Ghostscript
    gs_bin = shutil.which("gswin64c") or shutil.which("gs") or shutil.which("gswin32c")
    ghostscript_ok = bool(gs_bin or (settings.ghostscript_path and Path(settings.ghostscript_path).exists()))

    _cached_tool_status = {
        "redis": redis_ok,
        "gotenberg": gotenberg_ok,
        "soffice": soffice_bin is not None,
        "soffice_path": soffice_bin,
        "poppler": poppler_ok,
        "pandoc": pandoc_ok,
        "ghostscript": ghostscript_ok,
    }
    _last_tool_check = now
    return _cached_tool_status
