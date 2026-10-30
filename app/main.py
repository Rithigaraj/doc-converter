import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings, detect_tool_status
from app.schemas import HealthResponse
from app.api import convert, jobs, files, chat
from app.services.job_manager import purge_old_storage_files


async def periodic_purge():
    """Background task to regularly purge temporary files."""
    while True:
        try:
            await asyncio.sleep(3600)  # Check every hour
            purge_old_storage_files()
        except asyncio.CancelledError:
            break
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure directories and trigger initial purge
    for d in [settings.upload_dir, settings.output_dir, settings.tmp_dir]:
        d.mkdir(parents=True, exist_ok=True)
    purge_old_storage_files()
    purge_task = asyncio.create_task(periodic_purge())
    
    # Log detected tool statuses
    tools = detect_tool_status()
    print(f"[{settings.app_name}] Starting up. Tool Statuses: {tools}")
    
    yield
    
    # Shutdown
    purge_task.cancel()
    try:
        await purge_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    description="Full-featured Document Format Converter Service"
)

# Enable CORS for local development and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(convert.router, prefix="/api/convert", tags=["convert"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health_check():
    status_info = detect_tool_status()
    return HealthResponse(
        status="ok",
        redis=status_info["redis"],
        gotenberg=status_info["gotenberg"],
        soffice=status_info["soffice"],
        soffice_path=status_info["soffice_path"],
        poppler=status_info["poppler"],
        pandoc=status_info["pandoc"],
        ghostscript=status_info["ghostscript"],
    )


# Serve static web frontend
web_dir = Path(__file__).resolve().parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.get("/")
def index():
    index_file = web_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Doc Converter API", "docs": "/docs"}
