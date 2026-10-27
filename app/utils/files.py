import hashlib
import mimetypes
import os
import uuid
from pathlib import Path

from fastapi import UploadFile


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
    # basic sanitization
    base = Path(name).name.replace("..", "_").replace("\\", "_").replace("/", "_")
    return base


def new_job_id() -> str:
    return str(uuid.uuid4())


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


async def save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = safe_filename(upload.filename or "upload.bin")
    out_path = dest_dir / f"{new_job_id()}_{fname}"
    with out_path.open("wb") as f:
        content = await upload.read()
        f.write(content)
    return out_path
