from fastapi import APIRouter, HTTPException
from app.services.job_manager import get_job
from app.schemas import JobStatus

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatus)
def job_status(job_id: str):
    info = get_job(job_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return JobStatus(
        job_id=job_id,
        status=info.get("status", "queued"),
        progress=info.get("progress", 0),
        warnings=info.get("warnings", []),
        error=info.get("error"),
        outputs=info.get("outputs", []),
        files=info.get("files", []),
    )
