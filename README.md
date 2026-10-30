# Doc Converter (Full-Stack Document Conversion Service)

A reliable, full-featured document conversion service with modular converters, batch/ZIP packaging, isolated workers, and clear layout/scan warnings.

---

## Conversion Capabilities & Current Status

| Conversion Path | Engine | Status | Notes |
|---|---|---|---|
| **PDF → DOCX** | `pdf2docx` + `PyMuPDF` | **PASS** | Layout-aware extraction, preserved headings/tables. Scanned PDFs flagged. |
| **DOCX / Office → PDF** | `Gotenberg` / `LibreOffice` / `win32com` | **PASS** | High fidelity via Gotenberg (`/forms/libreoffice/convert`) or local `soffice`. |
| **PDF → XLSX** | `pdfplumber` + `openpyxl` | **PASS** | Table grid extraction into sheets; falls back to structured line parsing. |
| **PDF → PPTX** | `PyMuPDF` + `python-pptx` | **PASS** | High-resolution slide visual layout + searchable slide notes. |
| **XLSX → PDF** | `Gotenberg` / `LibreOffice` | **PASS** | Preserves sheets and page setup. |
| **PPTX → PDF** | `Gotenberg` / `LibreOffice` | **PASS** | Preserves presentation formatting. |
| **Image (PNG/JPG) → PDF** | `img2pdf` / `Pillow` | **PASS** | Direct lossless or quality-compressed PDF generation. |
| **PDF → Images (PNG/JPG)** | `PyMuPDF` / `pdf2image` | **PASS** | Native high-speed rendering; selectable DPI (72-600) and JPG quality (10-100). |
| **CSV ↔ XLSX** | `pandas` + `openpyxl` | **PASS** | Fast, lossless tabular conversion. |
| **HTML / TXT / RTF / ODT → PDF** | `ReportLab` / `Gotenberg` / `soffice` | **PASS** | Styled PDF output with heading and paragraph formatting. |
| **HTML / TXT / RTF / ODT → DOCX** | `python-docx` / `bs4` / `soffice` | **PASS** | Headings, bullet lists, and paragraphs converted to Word. |
| **Batch / ZIP Archives** | `zipfile` + parallel jobs | **PASS** | Upload multiple files or a ZIP archive, receive single or packaged ZIP download. |

---

## Architecture

- **FastAPI Application** (`app/main.py`)
  - `POST /api/convert`: Multipart upload supporting multiple files or ZIPs with target format and options.
  - `GET /api/jobs/{job_id}`: Polling endpoint returning `{status, progress, warnings, error, outputs}`.
  - `GET /api/download/{job_id}`: Direct file download (single converted file or `.zip` of all outputs).
  - `GET /api/health`: System diagnostics detecting Redis, Gotenberg, LibreOffice, and external tools.
- **Hybrid Worker Model**
  - **With Redis:** Distributed RQ workers running via `workers/rq_worker.py` (`rq.SimpleWorker` on Windows, standard `Worker` on Linux).
  - **Without Redis:** Automatic in-process background thread pool executor for zero-friction standalone local operation.
- **Modular Converters** (`converters/`)
  - Each converter inherits from `BaseConverter`, producing structured `ConvertResult(ok, output_path, warnings, meta, error)`.
- **Scheduled Storage Purge**
  - Automatic scheduled purge of temporary files in `uploads/`, `outputs/`, and `tmp/` based on `PURGE_AGE_HOURS`.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

### 3. Run the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Web Application: [http://localhost:8000](http://localhost:8000)
- Swagger API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Status: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## Running with Docker Compose (Recommended for Full Production Stack)

To run the complete stack with Redis, Gotenberg, FastAPI, and RQ Worker in one command:
```bash
docker compose up --build
```
This automatically provides:
- **FastAPI Server:** `http://localhost:8000`
- **Gotenberg (LibreOffice container):** `http://localhost:3000`
- **Redis Server:** `localhost:6379`
- **RQ Worker:** Background conversion queue

---

## Running Distributed RQ Worker on Windows

RQ workers traditionally rely on `os.fork()`, which is unsupported on Windows. Doc Converter includes native Windows support via `rq.SimpleWorker`:
```bash
python workers/rq_worker.py
```
*(If Redis is not running, the application automatically executes conversions through its internal background thread pool, ensuring 100% functionality without requiring Redis).*

---

## Verification & Testing

Run unit and integration test suite:
```bash
python -m pytest -v
```

Run live API end-to-end smoke test:
```bash
python scripts/smoke_test.py
```

---

## Troubleshooting

### 1. "No Office-to-PDF conversion engine available"
Office conversions (DOCX, PPTX, XLSX, ODT, RTF to PDF) require an engine:
- **Recommended:** Run Gotenberg via Docker: `docker compose up gotenberg` (or set `GOTENBERG_URL=http://localhost:3000` in `.env`).
- **Local Alternative:** Install [LibreOffice](https://www.libreoffice.org/) and ensure `soffice` is in your system PATH or configured via `SOFFICE_PATH` in `.env`.
- **Windows Alternative:** Microsoft Word/Excel/PowerPoint will be detected automatically if installed locally.

### 2. Redis Connection Refused (`Error 10061`)
If Redis is not running, Doc Converter automatically falls back to internal asynchronous execution. If you want full distributed queueing:
- Run Redis in Docker: `docker run -p 6379:6379 redis:7`
- Or use `docker compose up` to start all services simultaneously.

### 3. PDF to Images without Poppler
Doc Converter uses native PyMuPDF rendering by default, requiring **no** external Poppler binaries on Windows or Linux. If you wish to use `pdf2image`, install `poppler-utils` and specify `POPPLER_PATH` in `.env`.

---

## Document Intelligence & Chatbot Assistant (Gemini AI)

Doc Converter features a built-in document summarization and conversational intelligence assistant powered by Google Gemini.

### Setup
1. Get a Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).
2. Add your key to your `.env` file:
   ```env
   GEMINI_API_KEY=AIzaSy...
   GEMINI_MODEL=gemini-2.5-flash
   ```
3. Restart the server.

### Features
- **Multi-Format Extraction:** Automatically extracts text from PDF (with OCR for scanned files), DOCX, PPTX, XLSX, CSV, HTML, RTF, ODT, and images.
- **Selectable Summary Modes:** Executive Brief, Detailed, Structured Bullet Points, and Key Takeaways.
- **Map-Reduce for Large Documents:** Automatic chunked map-reduce summarization for high-volume files exceeding token budgets.
- **Conversational Q&A:** Grounded questions and answers streamed in real time via Server-Sent Events (SSE).
- **One-Click Conversion Workflow:** Any converted file can be immediately loaded into the intelligence chat via the "Summarise in Chat" button.
- **Summary Exports:** One-click export of generated summaries to TXT, Word (DOCX), or styled PDF.
- **Zero Content Logging:** Strict document confidentiality with automatic scheduled purging.
