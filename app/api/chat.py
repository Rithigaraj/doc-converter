import io
import json
import time
import uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.files import save_upload, safe_filename, new_job_id
from agent.text_extractor import extract_document_text, ExtractedDocument
from agent.llm_client import get_llm_provider

router = APIRouter()

# In-memory document session cache (protected, purged with scheduled cleanups)
CHAT_DOCUMENTS: dict[str, dict[str, Any]] = {}


class SummarizeRequest(BaseModel):
    doc_id: str
    style: str = "detailed"  # short | detailed | bullet_points | key_takeaways
    length: str = "standard"  # brief | standard | comprehensive


class ChatMessageRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str | None = None
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)


class ExportSummaryRequest(BaseModel):
    title: str = "Document Summary"
    text: str
    format: str = "pdf"  # txt | docx | pdf


@router.post("/upload")
async def chat_upload(
    file: UploadFile = File(None),
    existing_filename: str = Form(None)
):
    """
    Accepts either a new file upload or references an existing file from uploads/ or outputs/.
    Extracts text and caches for chat and summarization.
    """
    doc_id = new_job_id()
    extracted: ExtractedDocument | None = None

    if file and file.filename:
        saved_path = await save_upload(file, settings.upload_dir, max_mb=settings.max_upload_mb)
        extracted = extract_document_text(saved_path, filename=file.filename)
    elif existing_filename:
        # Check in outputs_dir or uploads_dir
        cleaned_name = Path(existing_filename).name
        target_path = settings.output_dir / cleaned_name
        if not target_path.exists():
            target_path = settings.upload_dir / cleaned_name
        if not target_path.exists():
            # Check prefix matches
            candidates = list(settings.output_dir.glob(f"*{cleaned_name}*"))
            if candidates:
                target_path = candidates[0]

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{existing_filename}' not found.")

        extracted = extract_document_text(target_path, filename=cleaned_name)
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or an existing_filename.")

    if not extracted:
        raise HTTPException(status_code=500, detail="Document text extraction failed.")

    preview_text = extracted.text[:400] + ("..." if len(extracted.text) > 400 else "")

    CHAT_DOCUMENTS[doc_id] = {
        "doc_id": doc_id,
        "filename": extracted.filename,
        "text": extracted.text,
        "page_count": extracted.page_count,
        "is_ocr": extracted.is_ocr,
        "warnings": extracted.warnings,
        "created_at": time.time(),
    }

    return {
        "doc_id": doc_id,
        "filename": extracted.filename,
        "char_count": len(extracted.text),
        "page_count": extracted.page_count,
        "is_ocr": extracted.is_ocr,
        "warnings": extracted.warnings,
        "preview": preview_text,
    }


@router.post("/summarize")
def summarize_document(req: SummarizeRequest):
    """Generate a structured summary for a document using Gemini."""
    doc = CHAT_DOCUMENTS.get(req.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document session not found or expired.")

    provider = get_llm_provider()
    summary_text = provider.summarize(
        text=doc["text"],
        style=req.style,
        length=req.length
    )

    return {
        "doc_id": req.doc_id,
        "filename": doc["filename"],
        "style": req.style,
        "length": req.length,
        "summary": summary_text,
        "warnings": doc["warnings"],
    }


@router.post("/message")
def chat_message(req: ChatMessageRequest):
    """Conversational question-answering grounded in the document context streamed via SSE."""
    doc_context = ""
    if req.doc_id and req.doc_id in CHAT_DOCUMENTS:
        doc_context = CHAT_DOCUMENTS[req.doc_id]["text"]

    provider = get_llm_provider()
    full_messages = list(req.history)
    full_messages.append({"role": "user", "content": req.message})

    def event_stream():
        try:
            for chunk in provider.chat_stream(full_messages, document_context=doc_context):
                payload = json.dumps({"chunk": chunk})
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            err_payload = json.dumps({"error": str(e)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/export-summary")
def export_summary(req: ExportSummaryRequest):
    """Export summary text to TXT, DOCX, or PDF."""
    fmt = req.format.lower().strip()
    safe_title = safe_filename(req.title)

    if fmt == "txt":
        buf = io.BytesIO(req.text.encode("utf-8"))
        return StreamingResponse(
            buf,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.txt"'}
        )

    elif fmt == "docx":
        from docx import Document
        doc = Document()
        doc.add_heading(req.title, level=1)
        for line in req.text.splitlines():
            if line.strip():
                if line.startswith("- ") or line.startswith("* "):
                    doc.add_paragraph(line[2:], style='List Bullet')
                else:
                    doc.add_paragraph(line)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.docx"'}
        )

    elif fmt == "pdf":
        import html
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        buf = io.BytesIO()
        pdf = SimpleDocTemplate(buf, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
        styles = getSampleStyleSheet()
        
        story = [
            Paragraph(f"<b>{html.escape(req.title)}</b>", styles['Title']),
            Spacer(1, 14)
        ]
        body_style = ParagraphStyle(
            'SummaryBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10.5,
            leading=15
        )
        for line in req.text.splitlines():
            if line.strip():
                story.append(Paragraph(html.escape(line), body_style))
                story.append(Spacer(1, 6))
            else:
                story.append(Spacer(1, 8))

        pdf.build(story)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.pdf"'}
        )

    raise HTTPException(status_code=400, detail=f"Unsupported export format: {fmt}")
