from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "doc-converter"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")
    tmp_dir: Path = Path("./tmp")
    max_upload_mb: int = 500
    purge_age_hours: int = 24

    redis_url: str = "redis://localhost:6379/0"
    rq_queue: str = "doc-jobs"

    office_path: str = "soffice"
    gotenberg_url: str | None = None
    poppler_path: str | None = None
    pandoc_path: str | None = None
    ghostscript_path: str | None = None



settings = Settings()

# ensure dirs
for d in [settings.upload_dir, settings.output_dir, settings.tmp_dir]:
    d.mkdir(parents=True, exist_ok=True)
