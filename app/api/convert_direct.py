import json
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.config import settings
from app.utils.files import save_upload, is_allowed, new_job_id
from app.utils.zip import unzip_to
from workers.tasks_direct import convert_job_direct

router = APIRouter()
jobs_store = {}


@router.post("/direct")
async def convert_direct(
    files: list[UploadFile] = File(...),
    target_ext: str = Form(...),
    options: str = Form("{}"),
):
    try:
        opts = json.loads(options)
    except Exception:
        opts = {}
    job_ids = []
    for upload in files:
        if not is_allowed(upload.filename or ""):
            raise HTTPException(status_code=400, detail=f"File type not allowed: {upload.filename}")
        saved = await save_upload(upload, settings.upload_dir)
        if saved.suffix.lower() == ".zip":
            extracted = unzip_to(saved, settings.tmp_dir)
            for ex in extracted:
                jid = new_job_id()
                try:
                    res = convert_job_direct(jid, str(ex), target_ext, opts)
                    jobs_store[jid] = {"status": "finished", "meta": res}
                except Exception as e:
                    jobs_store[jid] = {"status": "failed", "meta": {"error": str(e)}}
                job_ids.append(jid)
        else:
            jid = new_job_id()
            try:
                res = convert_job_direct(jid, str(saved), target_ext, opts)
                jobs_store[jid] = {"status": "finished", "meta": res}
            except Exception as e:
                jobs_store[jid] = {"status": "failed", "meta": {"error": str(e)}}
            job_ids.append(jid)
    return {"job_ids": job_ids}
