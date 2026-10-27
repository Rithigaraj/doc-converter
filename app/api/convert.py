import os
from pathlib import Path

import redis
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from rq import Queue

from app.config import settings
from app.utils.files import save_upload, is_allowed, new_job_id
from app.utils.zip import unzip_to
from workers.tasks import convert_job

router = APIRouter()
conn = redis.from_url(settings.redis_url)
q = Queue(settings.rq_queue, connection=conn)


@router.post("/")
async def convert(
    files: list[UploadFile] = File(...),
    target_ext: str = Form(...),
    options: str = Form("{}"),
):
    import json

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
                q.enqueue(convert_job, jid, str(ex), target_ext, opts, job_id=jid)
                job_ids.append(jid)
        else:
            jid = new_job_id()
            q.enqueue(convert_job, jid, str(saved), target_ext, opts, job_id=jid)
            job_ids.append(jid)
    return {"job_ids": job_ids}
