"""Test fallbacks EUR-Lex : PDF + OAI-PMH."""
import requests

CELEX = "32016R0679"  # RGPD — texte législatif bien connu
UA = "Mozilla/5.0 (compatible; Lexavo/1.0; +https://lexavo.be)"

tests = [
    ("PDF FR", f"https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:{CELEX}",
     {"User-Agent": UA}),
    ("OAI-PMH", f"https://eur-lex.europa.eu/oai.do?verb=GetRecord&metadataPrefix=eur-lex&identifier={CELEX}",
     {"User-Agent": UA}),
    ("API REST search", f"https://eur-lex.europa.eu/search.html?scope=EURLEX&text={CELEX}&lang=fr&type=quick&qid=1",
     {"User-Agent": UA}),
]

for name, url, headers in tests:
    try:
        r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        ctype = r.headers.get("Content-Type", "")
        print(f"\n[{name}] {r.status_code} | len={len(r.content)} | ctype={ctype[:60]}")
        if r.status_code == 200:
            print(f"  Sample: {r.text[:200].replace(chr(10),' ')}")
    except Exception as e:
        print(f"\n[{name}] ERREUR: {e}")
