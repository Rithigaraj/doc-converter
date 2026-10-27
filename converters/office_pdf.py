from .docx_pdf import DocxToPdfConverter


class OfficeToPdfConverter(DocxToPdfConverter):
    name = "office_to_pdf"
    # same as docx->pdf using LibreOffice
