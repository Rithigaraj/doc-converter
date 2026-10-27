from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter()


@router.get("/download/{fname}")
def download(fname: str):
    # fname is basename
    p = settings.output_dir / Path(fname).name
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p), filename=p.name)
