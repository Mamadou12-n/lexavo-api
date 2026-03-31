"""OCR partagé pour Shield et Decode — pytesseract."""
import io
from typing import Optional


def extract_text_from_image(image_bytes: bytes, lang: str = "fra+nld") -> str:
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        raise RuntimeError("pytesseract et Pillow requis. pip install pytesseract Pillow")
    image = Image.open(io.BytesIO(image_bytes))
    raw_text = pytesseract.image_to_string(image, lang=lang)
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    return "\n".join(lines)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        import fitz
    except ImportError:
        raise RuntimeError("PyMuPDF requis. pip install PyMuPDF")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text = page.get_text().strip()
        if text:
            text_parts.append(text)
        else:
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            text_parts.append(extract_text_from_image(img_bytes))
    doc.close()
    return "\n\n".join(text_parts)
