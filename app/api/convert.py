import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.config import settings
from app.utils.files import save_upload, is_allowed, new_job_id
from app.utils.zip import unzip_to
from app.services.job_manager import submit_conversion_job, register_batch_job

router = APIRouter()


@router.post("")
@router.post("/")
async def convert(
    files: list[UploadFile] = File(...),
    target_ext: str = Form(...),
    options: str = Form("{}"),
):
    try:
        opts = json.loads(options) if options else {}
    except Exception:
        opts = {}

    target_clean = target_ext.lower().lstrip(".")
    if not target_clean:
        raise HTTPException(status_code=400, detail="Target extension must be specified.")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided for conversion.")

    sub_jobs: list[str] = []

    for upload in files:
        filename = upload.filename or "file.bin"
        if not is_allowed(filename):
            raise HTTPException(
                status_code=400,
                detail=f"File extension not supported for '{filename}'."
            )

        saved = await save_upload(upload, settings.upload_dir, max_mb=settings.max_upload_mb)

        if saved.suffix.lower() == ".zip":
            extracted = unzip_to(saved, settings.tmp_dir)
            valid_extracted = [ex for ex in extracted if is_allowed(ex.name)]
            if not valid_extracted:
                raise HTTPException(status_code=400, detail="ZIP archive contains no supported files to convert.")
            for ex in valid_extracted:
                jid = new_job_id()
                submit_conversion_job(jid, ex, target_clean, opts)
                sub_jobs.append(jid)
        else:
            jid = new_job_id()
            submit_conversion_job(jid, saved, target_clean, opts)
            sub_jobs.append(jid)

    if not sub_jobs:
        raise HTTPException(status_code=400, detail="No valid files to convert.")

    if len(sub_jobs) == 1:
        primary_job_id = sub_jobs[0]
    else:
        primary_job_id = new_job_id()
        register_batch_job(primary_job_id, sub_jobs)

    return {
        "job_id": primary_job_id,
        "job_ids": sub_jobs,
        "count": len(sub_jobs),
        "target_ext": target_clean,
    }
