import io
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import pymupdf
import openpyxl

from app.main import app
from app.config import settings
from converters.registry import get_converter

client = TestClient(app)


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("samples")
    pdf_path = tmp / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=500)
    page.draw_rect(pymupdf.Rect(20, 20, 380, 480), color=(0.2, 0.4, 0.6))
    page.insert_text(pymupdf.Point(40, 60), "Doc Converter Test Sample PDF", fontsize=16)
    page.insert_text(pymupdf.Point(40, 100), "Header 1\tHeader 2\tHeader 3", fontsize=11)
    page.insert_text(pymupdf.Point(40, 120), "Row1Col1\tRow1Col2\tRow1Col3", fontsize=10)
    page.insert_text(pymupdf.Point(40, 140), "Row2Col1\tRow2Col2\tRow2Col3", fontsize=10)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture(scope="session")
def sample_png(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("samples")
    png_path = tmp / "sample.png"
    img = Image.new("RGB", (200, 200), color=(180, 200, 220))
    img.save(str(png_path), format="PNG")
    return png_path


@pytest.fixture(scope="session")
def sample_csv(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("samples")
    csv_path = tmp / "sample.csv"
    csv_path.write_text("ID,Name,Role\n1,Alice,Engineer\n2,Bob,Designer\n", encoding="utf-8")
    return csv_path


@pytest.fixture(scope="session")
def sample_txt(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("samples")
    txt_path = tmp / "sample.txt"
    txt_path.write_text("Title: Antigravity Converter\n\nThis is a sample text file.\nParagraph 2.\n", encoding="utf-8")
    return txt_path


@pytest.fixture(scope="session")
def sample_html(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("samples")
    html_path = tmp / "sample.html"
    html_path.write_text("<!DOCTYPE html><html><head><title>HTML Test</title></head><body><h1>Document Heading</h1><p>Test paragraph content.</p></body></html>", encoding="utf-8")
    return html_path


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "redis" in data
    assert "gotenberg" in data
    assert "soffice" in data


def test_pdf_to_docx(sample_pdf, tmp_path):
    out = tmp_path / "out.docx"
    conv = get_converter("pdf", "docx")
    assert conv is not None
    res = conv.convert(sample_pdf, out)
    assert res.ok
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_to_xlsx(sample_pdf, tmp_path):
    out = tmp_path / "out.xlsx"
    conv = get_converter("pdf", "xlsx")
    assert conv is not None
    res = conv.convert(sample_pdf, out)
    assert res.ok
    assert out.exists()
    wb = openpyxl.load_workbook(str(out))
    assert len(wb.sheetnames) >= 1


def test_pdf_to_pptx(sample_pdf, tmp_path):
    out = tmp_path / "out.pptx"
    conv = get_converter("pdf", "pptx")
    assert conv is not None
    res = conv.convert(sample_pdf, out)
    assert res.ok
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_to_images(sample_pdf, tmp_path):
    out = tmp_path / "out.png"
    conv = get_converter("pdf", "png")
    assert conv is not None
    res = conv.convert(sample_pdf, out, {"dpi": 100})
    assert res.ok
    assert res.output_path and res.output_path.exists()
    assert res.meta.get("count", 0) >= 1


def test_image_to_pdf(sample_png, tmp_path):
    out = tmp_path / "out.pdf"
    conv = get_converter("png", "pdf")
    assert conv is not None
    res = conv.convert(sample_png, out)
    assert res.ok
    assert out.exists()
    assert out.stat().st_size > 0


def test_csv_to_xlsx_and_back(sample_csv, tmp_path):
    out_xlsx = tmp_path / "out.xlsx"
    conv1 = get_converter("csv", "xlsx")
    assert conv1 is not None
    res1 = conv1.convert(sample_csv, out_xlsx)
    assert res1.ok
    assert out_xlsx.exists()

    out_csv = tmp_path / "back.csv"
    conv2 = get_converter("xlsx", "csv")
    assert conv2 is not None
    res2 = conv2.convert(out_xlsx, out_csv)
    assert res2.ok
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8")
    assert "Alice" in content


def test_txt_conversions(sample_txt, tmp_path):
    out_docx = tmp_path / "out.docx"
    conv_docx = get_converter("txt", "docx")
    assert conv_docx is not None
    res1 = conv_docx.convert(sample_txt, out_docx)
    assert res1.ok
    assert out_docx.exists()

    out_pdf = tmp_path / "out.pdf"
    conv_pdf = get_converter("txt", "pdf")
    assert conv_pdf is not None
    res2 = conv_pdf.convert(sample_txt, out_pdf)
    assert res2.ok
    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 0


def test_html_conversions(sample_html, tmp_path):
    out_docx = tmp_path / "out.docx"
    conv = get_converter("html", "docx")
    assert conv is not None
    res1 = conv.convert(sample_html, out_docx)
    assert res1.ok
    assert out_docx.exists()

    out_pdf = tmp_path / "out.pdf"
    conv_pdf = get_converter("html", "pdf")
    assert conv_pdf is not None
    res2 = conv_pdf.convert(sample_html, out_pdf)
    assert res2.ok
    assert out_pdf.exists()


def test_api_convert_and_poll_flow(sample_txt):
    with open(sample_txt, "rb") as f:
        response = client.post(
            "/api/convert",
            files=[("files", ("test.txt", f, "text/plain"))],
            data={"target_ext": "docx"}
        )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Poll until finished (direct/local worker is fast)
    import time
    status_data = None
    for _ in range(30):
        res = client.get(f"/api/jobs/{job_id}")
        assert res.status_code == 200
        status_data = res.json()
        if status_data["status"] in {"finished", "failed"}:
            break
        time.sleep(0.2)

    assert status_data is not None
    assert status_data["status"] == "finished"
    assert len(status_data["outputs"]) >= 1

    # Test download
    dl_res = client.get(f"/api/download/{job_id}")
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 0


def test_batch_zip_conversion(sample_txt, sample_csv, tmp_path):
    # Create an input ZIP containing sample.txt and sample.csv
    zip_in = tmp_path / "batch.zip"
    with zipfile.ZipFile(zip_in, "w") as z:
        z.write(sample_txt, arcname="item1.txt")
        z.write(sample_csv, arcname="item2.csv")

    with open(zip_in, "rb") as f:
        res = client.post(
            "/api/convert",
            files=[("files", ("batch.zip", f, "application/zip"))],
            data={"target_ext": "xlsx"}
        )
    assert res.status_code == 200
    data = res.json()
    job_id = data["job_id"]
    assert len(data["job_ids"]) >= 1

    import time
    status_data = None
    for _ in range(30):
        status_res = client.get(f"/api/jobs/{job_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        if status_data["status"] in {"finished", "failed"}:
            break
        time.sleep(0.3)

    assert status_data is not None
    assert status_data["status"] == "finished"
    assert len(status_data["outputs"]) >= 1
