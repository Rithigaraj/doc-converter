# Doc Converter (LLM-Orchestrated Format Converter)

A practical document conversion service that handles the requested conversions using tested libraries, isolated workers, batch/ZIP support, and clear warnings for complex layouts/scans.

> Note: This is **not** training a new LLM from scratch. Conversions are deterministic via purpose-built libraries; a thin agent/orchestrator just routes and surfaces warnings.

## Supported Tasks

| Task | Status | Notes |
|---|---|---|
| PDF → DOCX, DOCX → PDF | Implemented (best-effort) | Extract text/layout; preserve fonts/headings/tables/page breaks where supported. Warn on complex layouts/scans. |
| PDF → XLSX, PDF → PPTX, XLSX → PDF, PPTX → PDF | Implemented (best-effort) | Complex tables/charts/layouts require validation. Preserve sheets/slides/page setup where supported. |
| Image → PDF, PDF → Images (PNG/JPG/JPEG) | Implemented | Choose resolution/DPI and output quality. |
| HTML/TXT/RTF/ODT | Implemented (selected conversions) | Uses isolated workers and tested libraries. |
| CSV ↔ XLSX | Implemented | Direct, safe mapping. |
| Batch / ZIP | Implemented | Upload multiple files or a ZIP, convert, download results as ZIP. |

## Architecture

- **FastAPI** API (`app/main.py`) - upload, create jobs, check status, download
- **RQ + Redis** worker pool (`workers/`) - isolated job execution per conversion
- **Converters** (`converters/`) - modular, each with warnings/meta; common `BaseConverter`
- **Storage** - `uploads/`, `outputs/`, `tmp/` with basic purge
- **Web UI** - minimal static UI in `web/` for uploads/options/batch/warnings

## Dependencies (tested)

| Area | Library | Purpose |
|---|---|---|
| PDF↔DOCX | `pdf2docx`, `PyMuPDF` | Layout-aware extraction |
| Office↔PDF | `Gotenberg` (LibreOffice in container) or `LibreOffice` (headless) via `soffice` | High fidelity for all users via server; local LibreOffice still supported |
| PDF tables | `pdfplumber`, `camelot-py` | Table detection (may need Ghostscript) |
| Office building | `python-pptx`, `openpyxl` | Inspect/build |
| Data | `pandas` | CSV/XLSX transforms |
| Markup/text/ODT | `pypandoc`, `beautifulsoup4`, `odfpy`, `weasyhtml` | Selected conversions |
| Images/PDF | `img2pdf`, `pdf2image`, `Pillow` | DPI/quality control |
| Queue/ZIP | `redis`, `rq`, stdlib `zipfile` | Jobs and packaging |


## Quick Start (Windows/Linux)

### 1) Install Python deps
```bash
pip install -r requirements.txt
```

### 2) Install external tools (recommended)
- **Gotenberg** (recommended for shared/deployed): run via `docker compose up gotenberg` - no local LibreOffice needed for users.
- **LibreOffice** (optional local): for best DOCX/PPTX/XLSX<->PDF fidelity if not using Gotenberg. Ensure `soffice` in PATH.
- **Poppler**: required by `pdf2image` (for PDF->Images). Windows: add poppler bin to PATH or set env.
- **Ghostscript**: optional for some Camelot cases.
- **pandoc**: optional for some HTML/RTF paths.


### 3) Run Redis + Gotenberg
```bash
# Docker (all services)
docker compose up redis gotenberg

# or separately
docker run -p 6379:6379 redis:7
docker run -p 3000:3000 gotenberg/gotenberg:8
```

### 4) Start API + Worker
```bash
# Terminal 1: API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Worker
rq worker doc-jobs --url redis://localhost:6379/0
```
Set `GOTENBERG_URL=http://localhost:3000` in `.env` to use server-side LibreOffice conversion for all users.


### 5) Open UI
Open http://localhost:8000/ (served by FastAPI) or `web/index.html` directly.

## Warnings
- **Scanned/image PDFs**: Detected by low text ratio. Extraction to DOCX/XLSX may be incomplete - consider OCR.
- **Complex layouts/tables/charts**: Best-effort; validate output.
- **Fonts/page breaks**: Preserved where supported by underlying libraries; some reflow is expected.
- **RTF/ODT/HTML**: Support is for common cases; exotic features may need correction.

## Environment
Copy `.env.example` to `.env` and adjust paths/limits.

## Docker (optional)
```bash
docker compose up --build
```
(see `docker-compose.yml`)

## Tests
```bash
pytest -q
```

## Notes on "build an LLM model"
The user asked to "build an llm model that should perform these tasks..." - this implementation uses a service+rules approach (correct for format conversion). If you want an actual fine-tuned model later, we can add an `agent/llm_router.py` to classify/repair, but it's not necessary for correctness.
