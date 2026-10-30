import os
import shutil
from pathlib import Path
from rq import get_current_job

from app.config import settings
from app.utils.zip import zip_files
from converters.registry import get_converter


def convert_job(job_id: str, input_path: str, target_ext: str, options: dict | None = None) -> dict:
    options = options or {}
    job = get_current_job()
    if job:
        job.meta["status"] = "started"
        job.meta["progress"] = 20
        job.meta["warnings"] = []
        job.meta["error"] = None
        job.meta["outputs"] = []
        job.save_meta()

    in_path = Path(input_path).resolve()
    out_dir = settings.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    src_ext = in_path.suffix
    clean_target = target_ext.lower().lstrip(".")

    conv = get_converter(src_ext, clean_target)
    warnings_all: list[str] = []

    try:
        if conv is None:
            raise ValueError(f"No converter registered for {src_ext} -> {target_ext}")

        if job:
            job.meta["progress"] = 40
            job.save_meta()

        out_name = f"{in_path.stem}.{clean_target}"
        out_path = out_dir / f"{job_id}_{out_name}"

        res = conv.convert(in_path, out_path, options)
        if not res.ok:
            raise RuntimeError(res.error or "Conversion failed")

        warnings_all.extend(res.warnings)

        if job:
            job.meta["progress"] = 80
            job.save_meta()

        result_files: list[Path] = []
        # Multi-image output handling
        if clean_target in {"png", "jpg", "jpeg"} or (res.meta and res.meta.get("images")):
            images = res.meta.get("images") or []
            if images:
                result_files = [Path(p).resolve() for p in images if Path(p).exists()]
            elif res.output_path and res.output_path.exists():
                result_files = [res.output_path.resolve()]
        else:
            if res.output_path and res.output_path.exists():
                result_files = [res.output_path.resolve()]

        if not result_files:
            raise RuntimeError("Conversion completed but no output files were produced")

        final_files: list[Path] = []
        # If multiple output files generated, package them into a ZIP
        if len(result_files) > 1:
            zip_path = out_dir / f"{job_id}_converted.zip"
            zip_files(result_files, zip_path)
            # Both ZIP and individual files available
            final_files = [zip_path] + result_files
        else:
            final_files = result_files

        output_names = [p.name for p in final_files]

        if job:
            job.meta["status"] = "finished"
            job.meta["progress"] = 100
            job.meta["files"] = output_names
            job.meta["outputs"] = output_names
            job.meta["warnings"] = warnings_all
            job.meta["error"] = None
            job.save_meta()

        return {
            "status": "finished",
            "progress": 100,
            "files": output_names,
            "outputs": output_names,
            "warnings": warnings_all,
            "error": None,
        }
    except Exception as e:
        err_msg = str(e)
        if job:
            job.meta["status"] = "failed"
            job.meta["progress"] = 100
            job.meta["error"] = err_msg
            job.meta["warnings"] = warnings_all
            job.meta["outputs"] = []
            job.save_meta()
        raise
