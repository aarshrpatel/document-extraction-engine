import io
from pathlib import Path

import fitz  # pymupdf
from PIL import Image


def load_document(file_path: str | Path) -> list[tuple[Image.Image, int]]:
    """Load a PDF or image file and return a list of (page_image, page_number) tuples.

    For PDFs, each page is rendered as an image.
    For images (JPG/PNG), returns a single-element list.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _load_pdf(file_path)
    elif suffix in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"):
        return _load_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def load_document_from_bytes(
    file_bytes: bytes, filename: str
) -> list[tuple[Image.Image, int]]:
    """Load a document from bytes."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return _load_pdf_from_bytes(file_bytes)
    elif suffix in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"):
        img = Image.open(io.BytesIO(file_bytes))
        img.load()
        return [(img, 1)]
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _load_pdf(file_path: Path) -> list[tuple[Image.Image, int]]:
    doc = fitz.open(str(file_path))
    return _render_pages(doc)


def _load_pdf_from_bytes(file_bytes: bytes) -> list[tuple[Image.Image, int]]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return _render_pages(doc)


def _render_pages(doc: fitz.Document) -> list[tuple[Image.Image, int]]:
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render at 300 DPI for good OCR quality
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append((img, page_num + 1))
    doc.close()
    return pages


def _load_image(file_path: Path) -> list[tuple[Image.Image, int]]:
    img = Image.open(file_path)
    img.load()
    return [(img, 1)]
