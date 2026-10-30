from workers.tasks import convert_job


def convert_job_direct(job_id: str, input_path: str, target_ext: str, options: dict | None = None) -> dict:
    return convert_job(job_id, input_path, target_ext, options)
