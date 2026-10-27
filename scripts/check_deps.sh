#!/usr/bin/env bash
echo "Checking external tools..."
command -v soffice >/dev/null && echo "LibreOffice: OK" || echo "LibreOffice: MISSING"
command -v pdftoppm >/dev/null && echo "Poppler: OK" || echo "Poppler: MISSING (pdf2image)"
command -v gs >/dev/null && echo "Ghostscript: OK" || echo "Ghostscript: MISSING"
command -v pandoc >/dev/null && echo "Pandoc: OK" || echo "Pandoc: MISSING"
python -c "import fitz, pdf2docx, pdfplumber, openpyxl, pandas, pptx, img2pdf, pdf2image, PIL" && echo "Python deps: OK" || echo "Python deps: MISSING"
