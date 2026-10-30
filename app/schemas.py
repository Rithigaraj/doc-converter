from pydantic import BaseModel, Field


class ConvertRequest(BaseModel):
    target_ext: str
    options: dict | None = None


class JobStatus(BaseModel):
    job_id: str
    status: str = Field(description="Status of job: queued, started, finished, or failed")
    progress: int = Field(default=0, ge=0, le=100)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    outputs: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    redis: bool
    gotenberg: bool
    soffice: bool
    soffice_path: str | None = None
    poppler: bool
    pandoc: bool
    ghostscript: bool
