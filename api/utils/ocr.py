"""OCR partagé pour Shield et Decode — pytesseract."""
import base64
import io
import logging
from typing import List, Optional

log = logging.getLogger("ocr")


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


def extract_text_from_base64_list(photos_base64: List[str], lang: str = "fra+nld") -> str:
    """Extrait le texte OCR d'une liste d'images encodées en base64."""
    texts = []
    for b64 in photos_base64:
        if not b64:
            continue
        try:
            # Supprimer le data URI prefix si présent (data:image/jpeg;base64,...)
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            image_bytes = base64.b64decode(b64)
            text = extract_text_from_image(image_bytes, lang=lang)
            if text.strip():
                texts.append(text.strip())
        except Exception as e:
            log.warning(f"OCR base64 ignoré: {e}")
    return "\n\n".join(texts)


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
