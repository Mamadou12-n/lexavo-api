"""Scraper PDF pour les 4 codes belges hors périmètre coord HTML.

CLAUDE.md compliance :
- §1 zéro invention : URLs PDF vérifiées sur sources officielles (ejustice.just.fgov.be, wallex.wallonie.be)
- §8 vérifier 2× : taille PDF + chars extraits

Codes à scraper (PDF only) :
1. Code rural (1886) — ejustice
2. Code forestier wallon (2008) — wallex
3. Code wallon agriculture (2014) — wallex
4. Code bruxellois logement (2003 réécrit 2013) — ejustice
"""
import json
import sys
from pathlib import Path
import requests

JUSTEL_DIR = Path("output/justel")

CODES_PDF = [
    {
        "numac": "1886100750",
        "title": "Code rural (7 octobre 1886)",
        "url": "https://www.ejustice.just.fgov.be/img_l/pdf/1886/10/07/1886100750_F.pdf",
        "source": "JUSTEL",
        "date": "1886-10-07",
        "jurisdiction": "Belgium",
    },
    {
        "numac": "2003031392",
        "title": "Code bruxellois du logement",
        "url": "https://www.ejustice.just.fgov.be/img_l/pdf/2003/07/17/2003031392_F.pdf",
        "source": "JUSTEL",
        "date": "2003-07-17",
        "jurisdiction": "Bruxelles-Capitale",
    },
    {
        "numac": "2008203215",
        "title": "Code forestier wallon (15 juillet 2008)",
        "url": "https://www.ejustice.just.fgov.be/img_l/pdf/2008/07/15/2008203215_F.pdf",
        "source": "JUSTEL",
        "date": "2008-07-15",
        "jurisdiction": "Wallonie",
    },
    {
        "numac": "2014027151",
        "title": "Code wallon de l'agriculture (27 mars 2014)",
        "url": "https://www.ejustice.just.fgov.be/img_l/pdf/2014/03/27/2014027151_F.pdf",
        "source": "JUSTEL",
        "date": "2014-03-27",
        "jurisdiction": "Wallonie",
    },
]


def extract_pdf_text(pdf_bytes):
    """Extract text from PDF bytes using pdfplumber."""
    import io
    try:
        import pdfplumber
    except ImportError:
        print("[ERR] pdfplumber non installé, fallback sur PyPDF2")
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text
        except ImportError:
            print("[ERR] PyPDF2 non plus, install requis")
            return None

    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Lexavo legal scraper)",
    }
    saved = 0
    for code in CODES_PDF:
        numac = code["numac"]
        out_file = JUSTEL_DIR / f"{numac}_coord.json"
        title = code["title"]
        url = code["url"]
        print(f"\n=== {title} ===")
        print(f"  URL : {url}")

        try:
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not r.content.startswith(b"%PDF"):
                print(f"  [KO] Pas un PDF (Content-Type: {content_type})")
                continue
            print(f"  PDF taille : {len(r.content):,} bytes")

            text = extract_pdf_text(r.content)
            if not text or len(text) < 1000:
                print(f"  [KO] Texte extrait trop court : {len(text) if text else 0} chars")
                continue

            doc = {
                "numac": numac,
                "cn": numac,
                "title": title,
                "source": code["source"],
                "doc_type": "code",
                "jurisdiction": code["jurisdiction"],
                "country": "Belgium",
                "language": "fr",
                "date": code["date"],
                "url": url,
                "full_text": text,
                "char_count": len(text),
                "best_endpoint": "pdf_official",
            }
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            print(f"  [OK] {len(text):,} chars sauvés dans {out_file.name}")
            saved += 1

        except Exception as e:
            print(f"  [ERR] {e}")

    print(f"\n=== TERMINE ===")
    print(f"Codes PDF scrapes : {saved}/{len(CODES_PDF)}")


if __name__ == "__main__":
    main()
