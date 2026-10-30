import hashlib
import os
import re
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile

ALLOWED_EXTS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif",
    ".html", ".htm", ".txt", ".rtf", ".odt",
    ".csv",
    ".zip",
}


def get_ext(name: str) -> str:
    return Path(name).suffix.lower()


def is_allowed(name: str) -> bool:
    return get_ext(name) in ALLOWED_EXTS


def safe_filename(name: str) -> str:
    """Sanitize filename to prevent directory traversal or invalid characters."""
    base = Path(name).name
    # Strip dangerous characters
    cleaned = re.sub(r'[^a-zA-Z0-9_.\-\s]', '_', base)
    # Ensure not empty
    if not cleaned or cleaned.startswith('.'):
        cleaned = f"document{cleaned}"
    return cleaned


def new_job_id() -> str:
    return str(uuid.uuid4())


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


async def save_upload(upload: UploadFile, dest_dir: Path, max_mb: int = 500) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = safe_filename(upload.filename or "upload.bin")
    out_path = dest_dir / f"{new_job_id()}_{fname}"
    
    max_bytes = max_mb * 1024 * 1024
    total_written = 0

    with out_path.open("wb") as f:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > max_bytes:
                out_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum allowed size of {max_mb} MB."
                )
            f.write(chunk)
            
    return out_path
