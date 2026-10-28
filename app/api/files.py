from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
import io
from zipfile import ZipFile

from app.config import settings

router = APIRouter()


@router.get("/download/{fname}")
def download(fname: str):
    p = settings.output_dir / Path(fname).name
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p), filename=p.name, media_type='application/octet-stream', headers={"Content-Disposition": f'attachment; filename="{p.name}"'})


@router.get("/download-page/{fname}")
def download_page(fname: str):
    p = settings.output_dir / Path(fname).name
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    html = f"""<html><head><title>Download</title></head><body>
    <h2>Ready to download</h2>
    <p>{p.name}</p>
    <a href="/api/download/{p.name}" download>Click here to download</a>
    <script>window.location.href='/api/download/{p.name}';</script>
    </body></html>"""
    return HTMLResponse(content=html)


@router.get("/download-all/{job_id}")
def download_all(job_id: str):
    files = []
    for p in settings.output_dir.glob(f"{job_id}_*"):
        files.append(p)
    if not files:
        raise HTTPException(status_code=404, detail="Files not found")
    if len(files) == 1:
        return FileResponse(str(files[0]), filename=files[0].name, media_type='application/octet-stream', headers={"Content-Disposition": f'attachment; filename="{files[0].name}"'})
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as z:
        for f in files:
            z.write(f, arcname=f.name)
    buf.seek(0)
    return StreamingResponse(buf, media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="converted_{job_id}.zip"'})


