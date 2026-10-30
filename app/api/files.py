import io
from pathlib import Path
from zipfile import ZipFile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse

from app.config import settings

router = APIRouter()


@router.get("/download/{identifier}")
def download_by_job_or_filename(identifier: str):
    """
    Downloads the output for a given job_id or specific filename.
    If multiple files were generated for the job, returns a ZIP archive.
    """
    # 1. First check if identifier is an exact filename in output_dir
    direct_path = settings.output_dir / Path(identifier).name
    if direct_path.exists() and direct_path.is_file():
        clean_name = direct_path.name
        # Remove UUID prefix if present for clean download name
        if "_" in clean_name and len(clean_name.split("_")[0]) >= 32:
            display_name = clean_name.split("_", 1)[1]
        else:
            display_name = clean_name
        return FileResponse(
            str(direct_path),
            filename=display_name,
            media_type='application/octet-stream',
            headers={"Content-Disposition": f'attachment; filename="{display_name}"'}
        )

    # 2. Check if identifier is a job_id with matching files
    job_files = list(settings.output_dir.glob(f"{identifier}_*"))
    if not job_files:
        # Check without suffix
        job_files = [p for p in settings.output_dir.iterdir() if identifier in p.name]

    if not job_files:
        raise HTTPException(status_code=404, detail="Requested file or job outputs not found.")

    # Check if a zip already exists for this job
    existing_zip = next((p for p in job_files if p.suffix.lower() == ".zip"), None)
    if existing_zip and existing_zip.exists():
        return FileResponse(
            str(existing_zip),
            filename=f"converted_{identifier}.zip",
            media_type='application/zip',
            headers={"Content-Disposition": f'attachment; filename="converted_{identifier}.zip"'}
        )

    # If single file, return it
    if len(job_files) == 1:
        f = job_files[0]
        clean_name = f.name
        if "_" in clean_name and len(clean_name.split("_")[0]) >= 32:
            display_name = clean_name.split("_", 1)[1]
        else:
            display_name = clean_name
        return FileResponse(
            str(f),
            filename=display_name,
            media_type='application/octet-stream',
            headers={"Content-Disposition": f'attachment; filename="{display_name}"'}
        )

    # If multiple files, stream a ZIP
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as z:
        for f in job_files:
            clean_name = f.name
            if "_" in clean_name and len(clean_name.split("_")[0]) >= 32:
                arc_name = clean_name.split("_", 1)[1]
            else:
                arc_name = clean_name
            z.write(f, arcname=arc_name)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="converted_{identifier}.zip"'}
    )


@router.get("/download-all/{job_id}")
def download_all(job_id: str):
    return download_by_job_or_filename(job_id)


@router.get("/download-page/{fname}")
def download_page(fname: str):
    p = settings.output_dir / Path(fname).name
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    html = f"""<!DOCTYPE html><html><head><title>Download</title></head><body>
    <h2>Ready to download</h2>
    <p>{p.name}</p>
    <a href="/api/download/{p.name}" download>Click here to download</a>
    <script>window.location.href='/api/download/{p.name}';</script>
    </body></html>"""
    return HTMLResponse(content=html)
