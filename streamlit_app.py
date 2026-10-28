import os
import json
from pathlib import Path

import requests
import streamlit as st

API_BASE = os.getenv("DOC_CONVERTER_API", "http://localhost:8000")

st.set_page_config(page_title="Doc Converter", layout="wide")

st.title("Doc Converter")
st.caption("PDF↔DOCX, Office↔PDF, Images↔PDF, HTML/TXT/RTF/ODT, CSV↔XLSX • Batch/ZIP • Warnings for complex layouts/scans")

with st.sidebar:
    st.header("Settings")
    api_base = st.text_input("API Base URL", value=API_BASE)
    use_direct = st.toggle("Use direct conversion (no Redis)", value=True)
    st.markdown("Make sure API is running.")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Upload & Convert")
    files = st.file_uploader(
        "Upload files (or a .ZIP)",
        accept_multiple_files=True,
        type=["pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "gif", "html", "htm", "txt", "rtf", "odt", "csv", "zip"],
    )
    target_ext = st.selectbox(
        "Convert to",
        options=["docx", "pdf", "xlsx", "pptx", "png", "jpg", "csv"],
        index=1,
    )
    with st.expander("Options"):
        dpi = st.number_input("DPI (PDF→Images)", min_value=72, max_value=600, value=200, step=50)
        quality = st.number_input("Image quality (JPG)", min_value=10, max_value=100, value=90, step=5)
    opts = {"dpi": int(dpi), "quality": int(quality)}
    if st.button("Start Conversion", type="primary"):
        if not files:
            st.error("Please upload at least one file.")
        else:
            data = {"target_ext": target_ext, "options": json.dumps(opts)}
            file_list = []
            for f in files:
                file_list.append(("files", (f.name, f.getvalue(), f.type or "application/octet-stream")))
            try:
                endpoint = f"{api_base}/api/convert/direct" if use_direct else f"{api_base}/api/convert/"
                res = requests.post(endpoint, data=data, files=file_list)
                if res.status_code != 200:
                    st.error(f"Error: {res.text}")
                else:
                    jids = res.json().get("job_ids", [])
                    st.success(f"Started {len(jids)} job(s)")
                    for jid in jids:
                        st.session_state.setdefault("jobs", []).append(jid)
            except Exception as e:
                st.error(str(e))

with col2:
    st.subheader("Jobs")
    if st.button("Refresh"):
        st.rerun()
    for jid in st.session_state.get("jobs", [])[::-1]:
        with st.container(border=True):
            st.code(jid)
            try:
                r = requests.get(f"{api_base}/api/jobs/{jid}")
                if r.status_code == 200:
                    data = r.json()
                    status = data.get("meta", {}).get("status") or data.get("status")
                    st.write(f"Status: **{status}**")
                    if status == "finished":
                        files_res = data.get("meta", {}).get("files", [])
                        warns = data.get("meta", {}).get("warnings", [])
                        if warns:
                            st.warning("\n".join(warns))
                        dl_all = f"{api_base}/api/download-all/{jid}"
                        st.markdown(f"[Download all (ZIP)]({dl_all})")
                        for fp in files_res:
                            name = Path(fp).name
                            dl = f"{api_base}/api/download/{name}"
                            st.markdown(f"[Download {name}]({dl})")


                    elif status == "failed":
                        st.error(data.get("meta", {}).get("error", "Failed"))
                        warns = data.get("meta", {}).get("warnings", [])
                        if warns:
                            st.warning("\n".join(warns))
                    else:
                        st.info("Processing...")
                else:
                    st.warning("Job not found")
            except Exception as e:
                st.error(str(e))

st.divider()
st.subheader("Warnings")
st.info("Complex layouts, scanned PDFs, and some tables/charts may require manual correction or OCR.")
