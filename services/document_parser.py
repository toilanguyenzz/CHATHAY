"""Document parser: extracts text from PDF, Word, and images."""

import os
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def parse_pdf(file_path: str, max_pages: int = 100) -> str:
    """Extract text from PDF using pdfplumber (fallback to PyMuPDF)."""
    text_parts = []

    try:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(total_pages, max_pages)

            for i in range(pages_to_read):
                page = pdf.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            if text_parts:
                result = "\n\n".join(text_parts)
                logger.info(f"PDF parsed with pdfplumber: {pages_to_read}/{total_pages} pages, {len(result)} chars")
                return result

    except Exception as e:
        logger.warning(f"pdfplumber failed, trying PyMuPDF: {e}")

    # Fallback to PyMuPDF
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_to_read = min(total_pages, max_pages)

        for i in range(pages_to_read):
            page = doc[i]
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(page_text)

        doc.close()

        if text_parts:
            result = "\n\n".join(text_parts)
            logger.info(f"PDF parsed with PyMuPDF: {pages_to_read}/{total_pages} pages, {len(result)} chars")
            return result

    except Exception as e:
        logger.error(f"PyMuPDF also failed: {e}")

    return ""


async def parse_docx(file_path: str) -> str:
    """Extract text from Word .docx file."""
    try:
        from docx import Document

        doc = Document(file_path)
        text_parts = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        # Also extract from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    text_parts.append(row_text)

        result = "\n".join(text_parts)
        logger.info(f"DOCX parsed: {len(text_parts)} paragraphs, {len(result)} chars")
        return result

    except Exception as e:
        logger.error(f"DOCX parsing failed: {e}")
        return ""


async def convert_pdf_to_images(file_path: str, max_pages: int = 10, dpi: int = 200) -> list[str]:
    """Convert PDF pages to PNG images for OCR fallback.
    
    Used when pdfplumber/PyMuPDF can't extract text (scanned/handwritten PDFs).
    Returns list of image file paths. Caller is responsible for cleanup.
    """
    image_paths = []
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_to_render = min(total_pages, max_pages)
        zoom = dpi / 72  # 72 is default PDF DPI
        matrix = fitz.Matrix(zoom, zoom)

        base_dir = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        for i in range(pages_to_render):
            page = doc[i]
            pix = page.get_pixmap(matrix=matrix)
            img_path = os.path.join(base_dir, f"{base_name}_page_{i+1}.png")
            pix.save(img_path)
            image_paths.append(img_path)
            logger.info(f"PDF page {i+1}/{pages_to_render} rendered to image: {pix.width}x{pix.height}")

        doc.close()
        logger.info(f"PDF converted to {len(image_paths)} images for OCR fallback")

    except Exception as e:
        logger.error(f"PDF to image conversion failed: {e}")
        # Cleanup any partially created files
        for path in image_paths:
            try:
                os.remove(path)
            except OSError:
                pass
        image_paths = []

    return image_paths


async def parse_image_ocr(file_path: str) -> Optional[str]:
    """
    Extract text from image using Gemini's vision capability.
    This avoids needing a separate Google Cloud Vision API key.
    Returns None if OCR should be handled by the AI summarizer directly.
    """
    # We return None here because Gemini can directly read images
    # The AI summarizer will handle image files directly via multimodal
    return None


def get_file_type(file_path: str) -> str:
    """Detect file type from extension."""
    ext = os.path.splitext(file_path)[1].lower()

    type_map = {
        ".pdf": "pdf",
        ".doc": "docx",
        ".docx": "docx",
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".bmp": "image",
        ".webp": "image",
        ".tiff": "image",
        ".tif": "image",
    }

    return type_map.get(ext, "unknown")


async def extract_text(file_path: str, max_pages: int = 100) -> tuple[str, str]:
    """
    Extract text from a document file.
    
    Returns:
        tuple: (extracted_text, file_type)
        If file_type is 'image', text will be empty (handled by AI directly)
    """
    file_type = get_file_type(file_path)

    if file_type == "pdf":
        text = await parse_pdf(file_path, max_pages)
        return text, file_type

    elif file_type == "docx":
        text = await parse_docx(file_path)
        return text, file_type

    elif file_type == "image":
        # Images will be sent directly to Gemini's vision model
        return "", file_type

    else:
        logger.warning(f"Unsupported file type: {file_type} ({file_path})")
        return "", "unknown"
