from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api import convert, jobs, files
from app.api import convert_direct

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(convert.router, prefix="/api/convert", tags=["convert"])
app.include_router(convert_direct.router, prefix="/api/convert", tags=["convert-direct"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(files.router, prefix="/api", tags=["files"])

# serve web
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.get("/")
def index():
    web_dir = Path(__file__).parent.parent / "web"
    index_file = web_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Doc Converter API", "docs": "/docs"}
