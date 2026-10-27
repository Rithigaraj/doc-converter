import os
import shutil
from pathlib import Path

from rq import get_current_job

from app.config import settings
from app.utils.detect import is_scanned_pdf
from app.utils.zip import zip_files
from converters.registry import get_converter


def convert_job(job_id: str, input_path: str, target_ext: str, options: dict | None = None):
    options = options or {}
    job = get_current_job()
    if job:
        job.meta["status"] = "running"
        job.save_meta()
    in_path = Path(input_path)
    out_dir = settings.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    src_ext = in_path.suffix
    conv = get_converter(src_ext, target_ext)
    result_files = []
    warnings_all = []
    try:
        if conv is None:
            raise ValueError(f"No converter registered for {src_ext} -> {target_ext}")
        # handle multi-image case
        out_name = in_path.stem + f".{target_ext.lstrip('.')}"
        out_path = out_dir / f"{job_id}_{out_name}"
        res = conv.convert(in_path, out_path, options)
        if not res.ok:
            raise RuntimeError(res.error or "Conversion failed")
        warnings_all.extend(res.warnings)
        # handle pdf->images producing multiple
        if target_ext.lstrip(".") in {"png", "jpg", "jpeg"} or (res.meta and res.meta.get("images")):
            images = res.meta.get("images") or []
            if images:
                img_paths = [Path(p) for p in images]
                result_files = img_paths
            else:
                if res.output_path and res.output_path.exists():
                    result_files = [res.output_path]
        else:
            if res.output_path and res.output_path.exists():
                result_files = [res.output_path]
        # package if multiple
        if len(result_files) > 1:
            zip_path = out_dir / f"{job_id}_results.zip"
            zip_files(result_files, zip_path)
            final = [zip_path]
        else:
            final = result_files
        if job:
            job.meta["status"] = "finished"
            job.meta["files"] = [str(p) for p in final]
            job.meta["warnings"] = warnings_all
            job.save_meta()
        return {"status": "ok", "files": [str(p) for p in final], "warnings": warnings_all}
    except Exception as e:
        if job:
            job.meta["status"] = "failed"
            job.meta["error"] = str(e)
            job.meta["warnings"] = warnings_all
            job.save_meta()
        raise
