"""
tool_fallback.py — Integration centralisee de tous les outils de scraping
Chaque outil est importe conditionnellement (pas d'erreur si absent).
"""

import logging
import subprocess
import sys
import re
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger("tool_fallback")

TOOLS_BASE = Path.home() / "Downloads"


# ═══════════════════════════════════════════════════════════════════════
# OUTIL 1 : requests + BeautifulSoup (toujours disponible)
# ═══════════════════════════════════════════════════════════════════════

def extract_with_requests(url: str, timeout: int = 30) -> Optional[str]:
    """Extraction basique avec requests + BS4."""
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Lexavo-Legal-DB/1.0 (educational; legal-data)"}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"

        soup = BeautifulSoup(r.text, "lxml")
        # Supprimer scripts, styles, nav
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return text if len(text) > 50 else None

    except Exception as e:
        log.warning(f"requests echoue pour {url}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
# OUTIL 2 : crawl4ai
# ═══════════════════════════════════════════════════════════════════════

def extract_with_crawl4ai(url: str) -> Optional[str]:
    """Extraction avec crawl4ai (anti-bot, LLM-ready markdown)."""
    crawl4ai_python = TOOLS_BASE / "crawl4ai" / ".venv" / "Scripts" / "python.exe"
    if not crawl4ai_python.exists():
        log.debug("crawl4ai non disponible")
        return None

    try:
        script = f"""
import asyncio
from crawl4ai import AsyncWebCrawler
async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="{url}")
        print(result.markdown if result.success else "")
asyncio.run(main())
"""
        result = subprocess.run(
            [str(crawl4ai_python), "-c", script],
            capture_output=True, text=True, timeout=120
        )
        text = result.stdout.strip()
        return text if len(text) > 50 else None

    except Exception as e:
        log.warning(f"crawl4ai echoue pour {url}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
# OUTIL 3 : docling (OCR pour PDFs scannes)
# ═══════════════════════════════════════════════════════════════════════

def extract_pdf_with_docling(pdf_path: str) -> Optional[str]:
    """Extraction PDF avec docling (supporte OCR)."""
    docling_python = TOOLS_BASE / "docling" / ".venv" / "Scripts" / "python.exe"
    if not docling_python.exists():
        log.debug("docling non disponible")
        return None

    try:
        script = f"""
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert("{pdf_path}")
print(result.document.export_to_markdown())
"""
        result = subprocess.run(
            [str(docling_python), "-c", script],
            capture_output=True, text=True, timeout=300
        )
        text = result.stdout.strip()
        return text if len(text) > 50 else None

    except Exception as e:
        log.warning(f"docling echoue pour {pdf_path}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
# OUTIL 4 : pdfplumber (PDF texte)
# ═══════════════════════════════════════════════════════════════════════

def extract_pdf_with_pdfplumber(pdf_path: str) -> Optional[str]:
    """Extraction PDF avec pdfplumber (PDF texte natif)."""
    try:
        import pdfplumber

        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)

        full_text = "\n\n".join(pages_text)
        return full_text if len(full_text) > 50 else None

    except Exception as e:
        log.warning(f"pdfplumber echoue pour {pdf_path}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
# OUTIL 5 : pymupdf4llm / pdf-to-markdown
# ═══════════════════════════════════════════════════════════════════════

def extract_pdf_with_pymupdf(pdf_path: str) -> Optional[str]:
    """Extraction PDF avec pymupdf4llm (markdown optimise LLM)."""
    try:
        import pymupdf4llm
        text = pymupdf4llm.to_markdown(pdf_path)
        return text if len(text) > 50 else None
    except ImportError:
        log.debug("pymupdf4llm non disponible")
        return None
    except Exception as e:
        log.warning(f"pymupdf4llm echoue pour {pdf_path}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
# OUTIL 6 : unstructured
# ═══════════════════════════════════════════════════════════════════════

def extract_with_unstructured(file_path: str) -> Optional[str]:
    """Extraction avec unstructured (multi-format)."""
    unstructured_python = TOOLS_BASE / "unstructured" / ".venv" / "Scripts" / "python.exe"
    if not unstructured_python.exists():
        log.debug("unstructured non disponible")
        return None

    try:
        script = f"""
from unstructured.partition.auto import partition
elements = partition(filename="{file_path}")
text = "\\n".join([str(el) for el in elements])
print(text)
"""
        result = subprocess.run(
            [str(unstructured_python), "-c", script],
            capture_output=True, text=True, timeout=300
        )
        text = result.stdout.strip()
        return text if len(text) > 50 else None

    except Exception as e:
        log.warning(f"unstructured echoue pour {file_path}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
# CHAINES DE FALLBACK PAR TYPE
# ═══════════════════════════════════════════════════════════════════════

def extract_pdf_from_bytes(pdf_bytes: bytes) -> Optional[str]:
    """Chaine complete pour PDF depuis des bytes en memoire.
    pdfplumber → pymupdf → docling → unstructured.
    Sauvegarde dans un fichier temporaire pour les outils qui en ont besoin.
    """
    # 1. pdfplumber (direct depuis bytes, pas besoin de fichier)
    try:
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t.strip())
            text = "\n\n".join(pages)
            if text and len(text) > 100:
                return text
    except Exception as e:
        log.warning(f"pdfplumber (bytes) echoue: {e}")

    # 2+ : outils necessitant un fichier sur disque
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # 2. pymupdf4llm
        log.info("Fallback pymupdf pour PDF bytes")
        text = extract_pdf_with_pymupdf(tmp_path)
        if text and len(text) > 100:
            return text

        # 3. docling (OCR)
        log.info("Fallback docling OCR pour PDF bytes")
        text = extract_pdf_with_docling(tmp_path)
        if text and len(text) > 100:
            return text

        # 4. unstructured
        log.info("Fallback unstructured pour PDF bytes")
        text = extract_with_unstructured(tmp_path)
        if text and len(text) > 100:
            return text

    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    return None


def extract_web_content(url: str) -> Optional[str]:
    """Chaine complete pour contenu web : requests → crawl4ai."""
    text = extract_with_requests(url)
    if text and len(text) > 100:
        return text

    log.info(f"Fallback crawl4ai pour {url}")
    text = extract_with_crawl4ai(url)
    if text and len(text) > 100:
        return text

    return None


def extract_pdf_content(pdf_path: str) -> Optional[str]:
    """Chaine complete pour PDF : pdfplumber → pymupdf → docling → unstructured."""
    # 1. pdfplumber (rapide, PDF texte natif)
    text = extract_pdf_with_pdfplumber(pdf_path)
    if text and len(text) > 100:
        return text

    # 2. pymupdf4llm (markdown)
    log.info(f"Fallback pymupdf pour {pdf_path}")
    text = extract_pdf_with_pymupdf(pdf_path)
    if text and len(text) > 100:
        return text

    # 3. docling (OCR si scanne)
    log.info(f"Fallback docling OCR pour {pdf_path}")
    text = extract_pdf_with_docling(pdf_path)
    if text and len(text) > 100:
        return text

    # 4. unstructured (dernier recours)
    log.info(f"Fallback unstructured pour {pdf_path}")
    text = extract_with_unstructured(pdf_path)
    if text and len(text) > 100:
        return text

    return None


# ═══════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════

def has_html_tags(text: str) -> bool:
    """Verifie si le texte contient du HTML residuel."""
    html_pattern = re.compile(r'<(div|span|table|tr|td|script|style|nav|header|footer|a href)[^>]*>', re.I)
    return bool(html_pattern.search(text))


def is_utf8_clean(text: str) -> bool:
    """Verifie que le texte est propre (pas de caracteres corrompus)."""
    try:
        text.encode("utf-8").decode("utf-8")
        # Verifier les caracteres de remplacement
        return "\ufffd" not in text
    except (UnicodeDecodeError, UnicodeEncodeError):
        return False


def contains_legal_content(text: str) -> bool:
    """Verifie que le texte semble etre du contenu juridique."""
    legal_keywords = [
        "article", "loi", "arrete", "decret", "ordonnance",
        "tribunal", "cour", "jugement", "arret", "attendu",
        "considerant", "disposition", "alinea", "paragraphe",
        "moniteur", "belgisch staatsblad", "wet", "besluit",
        "regulation", "directive", "decision", "judgment",
        "code", "chapitre", "section", "titre",
    ]
    text_lower = text.lower()
    matches = sum(1 for kw in legal_keywords if kw in text_lower)
    return matches >= 2


def validate_document(doc_id: str, text: str, url: str) -> list:
    """5 verifications d'integrite sur un document."""
    errors = []

    # V1 : Texte obtenu
    if not text or len(text) < 100:
        errors.append(f"Texte trop court ({len(text) if text else 0} chars)")

    # V2 : Texte complet (heuristique)
    if text and text.rstrip().endswith("..."):
        errors.append("Texte semble tronque (se termine par ...)")

    # V3 : Contenu juridique
    if text and not contains_legal_content(text):
        errors.append("Ne semble pas etre du contenu juridique")

    # V4 : Pas de HTML residuel
    if text and has_html_tags(text):
        errors.append("HTML residuel detecte")

    # V5 : Integrite encodage
    if text and not is_utf8_clean(text):
        errors.append("Caracteres corrompus detectes")

    return errors
