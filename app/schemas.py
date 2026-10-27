from pydantic import BaseModel


class ConvertRequest(BaseModel):
    target_ext: str
    options: dict | None = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    files: list[str] | None = None
    warnings: list[str] | None = None
    error: str | None = None
