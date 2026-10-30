#!/usr/bin/env python3
"""
scripts/smoke_test.py
Live API end-to-end smoke test for Doc Converter.
Executes conversion jobs through the live running server and prints a results table.
"""

import io
import sys
import time
import zipfile
from pathlib import Path
import httpx
from PIL import Image
import pymupdf
import openpyxl

API_BASE = "http://127.0.0.1:8000"


def create_sample_files(dir_path: Path) -> dict[str, Path]:
    dir_path.mkdir(parents=True, exist_ok=True)
    files = {}

    # 1. PDF
    pdf_path = dir_path / "smoke_sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=350, height=450)
    page.draw_rect(pymupdf.Rect(10, 10, 340, 440), color=(0.2, 0.3, 0.5))
    page.insert_text(pymupdf.Point(30, 50), "Doc Converter Smoke Test PDF", fontsize=14)
    page.insert_text(pymupdf.Point(30, 80), "HeaderA\tHeaderB\tHeaderC", fontsize=10)
    page.insert_text(pymupdf.Point(30, 100), "Data1\tData2\tData3", fontsize=9)
    doc.save(str(pdf_path))
    doc.close()
    files["pdf"] = pdf_path

    # 2. PNG
    png_path = dir_path / "smoke_sample.png"
    img = Image.new("RGB", (150, 150), color=(100, 150, 200))
    img.save(str(png_path), format="PNG")
    files["png"] = png_path

    # 3. CSV
    csv_path = dir_path / "smoke_sample.csv"
    csv_path.write_text("Item,Quantity,Price\nWidget,10,19.99\nGadget,5,49.99\n", encoding="utf-8")
    files["csv"] = csv_path

    # 4. XLSX
    xlsx_path = dir_path / "smoke_sample.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["Product", "Qty", "Amount"])
    ws.append(["Apples", 20, 40])
    wb.save(str(xlsx_path))
    files["xlsx"] = xlsx_path

    # 5. TXT
    txt_path = dir_path / "smoke_sample.txt"
    txt_path.write_text("Hello from smoke test!\nThis text document tests conversion.\n", encoding="utf-8")
    files["txt"] = txt_path

    # 6. HTML
    html_path = dir_path / "smoke_sample.html"
    html_path.write_text("<!DOCTYPE html><html><body><h1>Smoke Test</h1><p>HTML paragraph.</p></body></html>", encoding="utf-8")
    files["html"] = html_path

    # 7. Batch ZIP
    zip_path = dir_path / "smoke_batch.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.write(txt_path, arcname="batch_text.txt")
        z.write(csv_path, arcname="batch_data.csv")
    files["zip"] = zip_path

    return files


def run_live_conversion(client: httpx.Client, file_path: Path, target_ext: str, options: dict = None) -> tuple[bool, str]:
    options = options or {}
    try:
        with open(file_path, "rb") as f:
            files = [("files", (file_path.name, f, "application/octet-stream"))]
            res = client.post(
                f"{API_BASE}/api/convert",
                files=files,
                data={"target_ext": target_ext, "options": str(options).replace("'", '"')},
                timeout=15.0
            )

        if res.status_code != 200:
            return False, f"HTTP {res.status_code}: {res.text[:100]}"

        data = res.json()
        job_id = data.get("job_id")
        if not job_id:
            return False, "No job_id returned"

        # Poll status
        max_attempts = 40
        for _ in range(max_attempts):
            poll_res = client.get(f"{API_BASE}/api/jobs/{job_id}", timeout=5.0)
            if poll_res.status_code == 200:
                pdata = poll_res.json()
                st = pdata.get("status")
                if st == "finished":
                    # Verify download works
                    dl_res = client.get(f"{API_BASE}/api/download/{job_id}", timeout=10.0)
                    if dl_res.status_code == 200 and len(dl_res.content) > 0:
                        return True, "OK"
                    return False, f"Download failed ({dl_res.status_code})"
                elif st == "failed":
                    return False, pdata.get("error") or "Job marked as failed"
            time.sleep(0.3)

        return False, "Polling timed out"
    except Exception as e:
        return False, str(e)


def main():
    print(f"Connecting to live API at {API_BASE}...")
    with httpx.Client(timeout=5.0) as client:
        try:
            h = client.get(f"{API_BASE}/api/health")
            if h.status_code != 200:
                print(f"ERROR: API returned status {h.status_code} on /api/health")
                sys.exit(1)
            print(f"Health check: OK. System status: {h.json()}")
        except Exception as e:
            print(f"ERROR: Cannot reach live API at {API_BASE}. Ensure server is running.\nDetail: {e}")
            sys.exit(1)

        temp_dir = Path("./tmp/smoke_tests").resolve()
        samples = create_sample_files(temp_dir)

        test_cases = [
            ("PDF -> DOCX", samples["pdf"], "docx", {}),
            ("PDF -> XLSX", samples["pdf"], "xlsx", {}),
            ("PDF -> PPTX", samples["pdf"], "pptx", {}),
            ("PDF -> Images (PNG)", samples["pdf"], "png", {"dpi": 100}),
            ("Image (PNG) -> PDF", samples["png"], "pdf", {}),
            ("CSV -> XLSX", samples["csv"], "xlsx", {}),
            ("XLSX -> CSV", samples["xlsx"], "csv", {}),
            ("TXT -> DOCX", samples["txt"], "docx", {}),
            ("TXT -> PDF", samples["txt"], "pdf", {}),
            ("HTML -> PDF", samples["html"], "pdf", {}),
            ("Batch / ZIP -> XLSX", samples["zip"], "xlsx", {}),
        ]

        print("\n" + "=" * 50)
        print("RUNNING LIVE END-TO-END CONVERSION TESTS")
        print("=" * 50)

        results = []
        for name, fpath, target_ext, opts in test_cases:
            t0 = time.time()
            ok, msg = run_live_conversion(client, fpath, target_ext, opts)
            elapsed = time.time() - t0
            status_str = "PASS" if ok else "FAIL"
            results.append((name, status_str, f"{elapsed:.2f}s", msg))
            print(f"[{status_str}] {name:<22} ({elapsed:.2f}s) -> {msg}")

        print("\n" + "=" * 50)
        print("SMOKE TEST RESULTS TABLE")
        print("=" * 50)
        print(f"{'Conversion':<24} | {'Status':<6} | {'Time':<7} | {'Note'}")
        print("-" * 50)
        all_passed = True
        for name, status, elapsed, msg in results:
            print(f"{name:<24} | {status:<6} | {elapsed:<7} | {msg}")
            if status != "PASS":
                all_passed = False
        print("=" * 50)

        if all_passed:
            print("\nALL SMOKE TESTS PASSED!")
            sys.exit(0)
        else:
            print("\nSOME SMOKE TESTS FAILED!")
            sys.exit(1)


if __name__ == "__main__":
    main()
