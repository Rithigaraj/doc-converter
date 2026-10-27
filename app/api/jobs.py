from fastapi import APIRouter, HTTPException
try:
    from rq import Queue
    from rq.job import Job
    import redis

    from app.config import settings

    conn = redis.from_url(settings.redis_url)
    q = Queue(settings.rq_queue, connection=conn)
    HAS_REDIS = True
except Exception:
    HAS_REDIS = False

from app.api import convert_direct

router = APIRouter()


@router.get("/{job_id}")
def job_status(job_id: str):
    if HAS_REDIS:
        try:
            job = Job.fetch(job_id, connection=conn)
            return {
                "job_id": job_id,
                "status": job.get_status(),
                "result": job.result,
                "meta": job.meta,
            }
        except Exception:
            pass
    # fallback to direct store
    if job_id in convert_direct.jobs_store:
        return {"job_id": job_id, **convert_direct.jobs_store[job_id]}
    raise HTTPException(status_code=404, detail="Job not found")

