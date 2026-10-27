from pathlib import Path

from .pdf_docx import PdfToDocxConverter
from .docx_pdf import DocxToPdfConverter
from .pdf_xlsx import PdfToXlsxConverter
from .pdf_pptx import PdfToPptxConverter
from .office_pdf import OfficeToPdfConverter
from .image_pdf import ImageToPdfConverter
from .pdf_images import PdfToImagesConverter
from .html_txt_rtf_odt import HtmlTxtRtfOdtConverter
from .csv_xlsx import CsvXlsxConverter


REGISTRY = {
    ("pdf", "docx"): PdfToDocxConverter(),
    ("docx", "pdf"): DocxToPdfConverter(),
    ("doc", "pdf"): DocxToPdfConverter(),
    ("pdf", "xlsx"): PdfToXlsxConverter(),
    ("pdf", "pptx"): PdfToPptxConverter(),
    ("xlsx", "pdf"): OfficeToPdfConverter(),
    ("xls", "pdf"): OfficeToPdfConverter(),
    ("pptx", "pdf"): OfficeToPdfConverter(),
    ("ppt", "pdf"): OfficeToPdfConverter(),
    ("image", "pdf"): ImageToPdfConverter(),  # handled specially
    ("pdf", "images"): PdfToImagesConverter(),  # handled specially
    ("csv", "xlsx"): CsvXlsxConverter(),
    ("xlsx", "csv"): CsvXlsxConverter(),
    ("html", "pdf"): HtmlTxtRtfOdtConverter(),
    ("htm", "pdf"): HtmlTxtRtfOdtConverter(),
    ("txt", "pdf"): HtmlTxtRtfOdtConverter(),
    ("txt", "docx"): HtmlTxtRtfOdtConverter(),
    ("rtf", "pdf"): HtmlTxtRtfOdtConverter(),
    ("odt", "pdf"): HtmlTxtRtfOdtConverter(),
    ("odt", "docx"): HtmlTxtRtfOdtConverter(),
}


def get_converter(src_ext: str, dst_ext: str):
    src = src_ext.lower().lstrip(".")
    dst = dst_ext.lower().lstrip(".")
    if src in {"png", "jpg", "jpeg", "tif", "tiff", "bmp", "gif"}:
        src = "image"
    if dst == "png" or dst == "jpg" or dst == "jpeg":
        dst = "images"
    return REGISTRY.get((src, dst))
