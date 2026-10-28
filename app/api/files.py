from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import io
from zipfile import ZipFile

from app.config import settings

router = APIRouter()


@router.get("/download/{fname}")
def download(fname: str):
    p = settings.output_dir / Path(fname).name
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p), filename=p.name, media_type='application/octet-stream')


@router.get("/download-all/{job_id}")
def download_all(job_id: str):
    # find files for this job
    files = []
    for p in settings.output_dir.glob(f"{job_id}_*"):
        files.append(p)
    if not files:
        raise HTTPException(status_code=404, detail="Files not found")
    if len(files) == 1:
        return FileResponse(str(files[0]), filename=files[0].name, media_type='application/octet-stream')
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as z:
        for f in files:
            z.write(f, arcname=f.name)
    buf.seek(0)
    return StreamingResponse(buf, media_type='application/zip', headers={'Content-Disposition': f'attachment; filename=converted_{job_id}.zip'})

