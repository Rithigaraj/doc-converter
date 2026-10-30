from pathlib import Path
from .base import BaseConverter
from .pdf_docx import PdfToDocxConverter
from .docx_pdf import DocxToPdfConverter
from .pdf_xlsx import PdfToXlsxConverter
from .pdf_pptx import PdfToPptxConverter
from .office_pdf import OfficeToPdfConverter
from .image_pdf import ImageToPdfConverter
from .pdf_images import PdfToImagesConverter
from .html_txt_rtf_odt import HtmlTxtRtfOdtConverter
from .csv_xlsx import CsvXlsxConverter


_pdf_docx = PdfToDocxConverter()
_docx_pdf = DocxToPdfConverter()
_pdf_xlsx = PdfToXlsxConverter()
_pdf_pptx = PdfToPptxConverter()
_office_pdf = OfficeToPdfConverter()
_image_pdf = ImageToPdfConverter()
_pdf_images = PdfToImagesConverter()
_html_txt = HtmlTxtRtfOdtConverter()
_csv_xlsx = CsvXlsxConverter()

REGISTRY: dict[tuple[str, str], BaseConverter] = {
    # PDF to Office
    ("pdf", "docx"): _pdf_docx,
    ("pdf", "doc"): _pdf_docx,
    ("pdf", "xlsx"): _pdf_xlsx,
    ("pdf", "xls"): _pdf_xlsx,
    ("pdf", "pptx"): _pdf_pptx,
    ("pdf", "ppt"): _pdf_pptx,

    # Office to PDF
    ("docx", "pdf"): _docx_pdf,
    ("doc", "pdf"): _docx_pdf,
    ("xlsx", "pdf"): _office_pdf,
    ("xls", "pdf"): _office_pdf,
    ("pptx", "pdf"): _office_pdf,
    ("ppt", "pdf"): _office_pdf,

    # Images and PDF
    ("image", "pdf"): _image_pdf,
    ("png", "pdf"): _image_pdf,
    ("jpg", "pdf"): _image_pdf,
    ("jpeg", "pdf"): _image_pdf,
    ("bmp", "pdf"): _image_pdf,
    ("gif", "pdf"): _image_pdf,
    ("tif", "pdf"): _image_pdf,
    ("tiff", "pdf"): _image_pdf,

    ("pdf", "images"): _pdf_images,
    ("pdf", "png"): _pdf_images,
    ("pdf", "jpg"): _pdf_images,
    ("pdf", "jpeg"): _pdf_images,

    # CSV <-> XLSX
    ("csv", "xlsx"): _csv_xlsx,
    ("csv", "xls"): _csv_xlsx,
    ("xlsx", "csv"): _csv_xlsx,
    ("xls", "csv"): _csv_xlsx,
    ("txt", "xlsx"): _csv_xlsx,
    ("txt", "csv"): _csv_xlsx,

    # HTML / TXT / RTF / ODT
    ("html", "pdf"): _html_txt,
    ("htm", "pdf"): _html_txt,
    ("html", "docx"): _html_txt,
    ("htm", "docx"): _html_txt,
    ("txt", "pdf"): _html_txt,
    ("txt", "docx"): _html_txt,
    ("rtf", "pdf"): _html_txt,
    ("rtf", "docx"): _html_txt,
    ("odt", "pdf"): _html_txt,
    ("odt", "docx"): _html_txt,
}


def get_converter(src_ext: str, dst_ext: str) -> BaseConverter | None:
    src = src_ext.lower().lstrip(".")
    dst = dst_ext.lower().lstrip(".")
    
    if src in {"png", "jpg", "jpeg", "tif", "tiff", "bmp", "gif"}:
        if (src, dst) in REGISTRY:
            return REGISTRY[(src, dst)]
        return REGISTRY.get(("image", dst))
    
    if dst in {"png", "jpg", "jpeg"} and src == "pdf":
        return _pdf_images

    return REGISTRY.get((src, dst))
