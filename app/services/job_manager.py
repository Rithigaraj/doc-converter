import io
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.config import settings
from app.utils.zip import zip_files
from workers.tasks import convert_job

# Thread-safe in-memory job store for direct/fallback execution
_lock = threading.Lock()
LOCAL_JOBS: dict[str, dict[str, Any]] = {}
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="doc_worker")

_last_redis_check = 0.0
_redis_available = False


def is_redis_available() -> bool:
    """Check Redis with a short cache to prevent blocking on every request."""
    global _last_redis_check, _redis_available
    now = time.time()
    if now - _last_redis_check < 5.0:
        return _redis_available
    _last_redis_check = now
    try:
        import redis
        conn = redis.from_url(settings.redis_url, socket_connect_timeout=0.2)
        conn.ping()
        _redis_available = True
    except Exception:
        _redis_available = False
    return _redis_available


def _execute_local(job_id: str, input_path: str, target_ext: str, options: dict[str, Any]):
    with _lock:
        if job_id in LOCAL_JOBS:
            LOCAL_JOBS[job_id]["status"] = "started"
            LOCAL_JOBS[job_id]["progress"] = 30

    try:
        res = convert_job(job_id, input_path, target_ext, options)
        with _lock:
            LOCAL_JOBS[job_id]["status"] = "finished"
            LOCAL_JOBS[job_id]["progress"] = 100
            LOCAL_JOBS[job_id]["outputs"] = res.get("outputs", [])
            LOCAL_JOBS[job_id]["files"] = res.get("files", [])
            LOCAL_JOBS[job_id]["warnings"] = res.get("warnings", [])
            LOCAL_JOBS[job_id]["error"] = None
    except Exception as e:
        with _lock:
            LOCAL_JOBS[job_id]["status"] = "failed"
            LOCAL_JOBS[job_id]["progress"] = 100
            LOCAL_JOBS[job_id]["error"] = str(e)


def submit_conversion_job(job_id: str, input_path: Path, target_ext: str, options: dict[str, Any]) -> str:
    """Submit conversion job to RQ/Redis if available, otherwise to local ThreadPool."""
    options = options or {}
    use_redis = False

    if is_redis_available():
        try:
            import redis
            from rq import Queue
            conn = redis.from_url(settings.redis_url, socket_connect_timeout=0.5)
            q = Queue(settings.rq_queue, connection=conn)
            q.enqueue(convert_job, job_id, str(input_path), target_ext, options, job_id=job_id)
            use_redis = True
        except Exception:
            use_redis = False

    with _lock:
        LOCAL_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 5,
            "warnings": [],
            "error": None,
            "outputs": [],
            "files": [],
            "target_ext": target_ext,
            "input_file": str(input_path),
            "created_at": time.time(),
            "backend": "redis" if use_redis else "local",
        }

    if not use_redis:
        _executor.submit(_execute_local, job_id, str(input_path), target_ext, options)

    return job_id


def register_batch_job(master_id: str, sub_job_ids: list[str]):
    """Register a master batch job that aggregates multiple sub-jobs."""
    with _lock:
        LOCAL_JOBS[master_id] = {
            "job_id": master_id,
            "type": "batch",
            "backend": "local",
            "sub_jobs": sub_job_ids,
            "status": "queued",
            "progress": 0,
            "warnings": [],
            "error": None,
            "outputs": [],
            "files": [],
            "created_at": time.time(),
        }


def get_job(job_id: str) -> dict[str, Any] | None:
    """Fetch status for either single job or batch job."""
    with _lock:
        batch_info = LOCAL_JOBS.get(job_id)
        if batch_info and batch_info.get("type") == "batch":
            sub_ids = batch_info.get("sub_jobs", [])
            sub_statuses = []
            for sid in sub_ids:
                st_info = LOCAL_JOBS.get(sid)
                if st_info:
                    sub_statuses.append(st_info)
                elif is_redis_available():
                    sub_statuses.append(get_job(sid))

            all_finished = True
            any_started = False
            has_failed = False
            total_progress = 0
            all_warnings: list[str] = []
            all_outputs: list[str] = []
            errors: list[str] = []

            for s in sub_statuses:
                if not s:
                    all_finished = False
                    continue
                st = s.get("status", "queued")
                if st == "failed":
                    has_failed = True
                    all_finished = False
                    if s.get("error"):
                        errors.append(s["error"])
                elif st != "finished":
                    all_finished = False
                if st in {"started", "finished"}:
                    any_started = True
                total_progress += s.get("progress", 0)
                all_warnings.extend(s.get("warnings", []))
                for out in s.get("outputs", []):
                    if out not in all_outputs:
                        all_outputs.append(out)

            count = max(len(sub_ids), 1)
            avg_progress = int(total_progress / count)

            if all_finished:
                final_status = "finished"
                avg_progress = 100
                # Generate combined ZIP for batch if multiple outputs
                if len(all_outputs) > 1:
                    zip_name = f"{job_id}_batch_converted.zip"
                    zip_path = settings.output_dir / zip_name
                    if not zip_path.exists():
                        out_paths = [settings.output_dir / fname for fname in all_outputs if (settings.output_dir / fname).exists()]
                        if out_paths:
                            zip_files(out_paths, zip_path)
                    if zip_name not in all_outputs:
                        all_outputs.insert(0, zip_name)
            elif has_failed and (avg_progress >= 100 or len(sub_statuses) == len(sub_ids)):
                final_status = "failed" if not all_outputs else "finished"
            elif any_started:
                final_status = "started"
            else:
                final_status = "queued"

            return {
                "job_id": job_id,
                "status": final_status,
                "progress": avg_progress,
                "warnings": list(dict.fromkeys(all_warnings)),
                "error": "; ".join(errors) if errors else None,
                "outputs": all_outputs,
                "files": all_outputs,
            }

        # Check local in-memory store first
        if job_id in LOCAL_JOBS:
            info = LOCAL_JOBS[job_id]
            # If locally dispatched, return immediately without touching Redis
            if info.get("backend") == "local":
                return {
                    "job_id": job_id,
                    "status": info.get("status", "queued"),
                    "progress": info.get("progress", 0),
                    "warnings": info.get("warnings", []),
                    "error": info.get("error"),
                    "outputs": info.get("outputs", []),
                    "files": info.get("files", []),
                }

    # If Redis is available, check RQ
    if is_redis_available():
        try:
            import redis
            from rq.job import Job
            conn = redis.from_url(settings.redis_url, socket_connect_timeout=0.3)
            rq_job = Job.fetch(job_id, connection=conn)
            meta = rq_job.meta or {}
            rq_status = rq_job.get_status()
            status_map = {
                "queued": "queued",
                "started": "started",
                "finished": "finished",
                "failed": "failed",
                "deferred": "queued",
                "scheduled": "queued",
            }
            status = meta.get("status") or status_map.get(rq_status, "queued")
            outputs = meta.get("outputs") or meta.get("files") or []

            return {
                "job_id": job_id,
                "status": status,
                "progress": meta.get("progress", 100 if status == "finished" else (30 if status == "started" else 0)),
                "warnings": meta.get("warnings", []),
                "error": meta.get("error") or (str(rq_job.exc_info) if rq_status == "failed" else None),
                "outputs": outputs,
                "files": outputs,
            }
        except Exception:
            pass

    # Check disk for completed files as fallback
    produced_files = list(settings.output_dir.glob(f"{job_id}_*"))
    if produced_files:
        fnames = [p.name for p in produced_files]
        return {
            "job_id": job_id,
            "status": "finished",
            "progress": 100,
            "warnings": [],
            "error": None,
            "outputs": fnames,
            "files": fnames,
        }

    return None


def purge_old_storage_files():
    """Purge files older than settings.purge_age_hours."""
    now = time.time()
    cutoff_seconds = settings.purge_age_hours * 3600
    cleaned_count = 0
    for folder in [settings.tmp_dir, settings.upload_dir, settings.output_dir]:
        if not folder.exists():
            continue
        for p in folder.glob("*"):
            try:
                if p.is_file() and (now - p.stat().st_mtime) > cutoff_seconds:
                    p.unlink(missing_ok=True)
                    cleaned_count += 1
            except Exception:
                pass
    return cleaned_count
