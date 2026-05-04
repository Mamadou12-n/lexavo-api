"""Test CELLAR xhtml+xml sur fichiers LEG_ (législation EUR-Lex)."""
import json, pathlib, requests

p = pathlib.Path(r"C:\Users\bahma\Downloads\base-juridique-app\output\eurlex")
tested = 0
ok = 0
for f in sorted(p.glob("LEG_*.json"))[:100]:
    d = json.loads(f.read_text(encoding="utf-8"))
    wu = d.get("work_uri", "")
    celex = d.get("celex", "")
    if not wu or not celex:
        continue
    uuid = wu.split("/")[-1] if wu else ""
    if not uuid or len(uuid) < 10:
        continue
    try:
        url = f"https://publications.europa.eu/resource/cellar/{uuid}"
        r = requests.get(url, headers={"Accept": "application/xhtml+xml", "Accept-Language": "fr"},
                         timeout=10, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 200:
            print(f"OK  {celex} | {len(r.text)} chars")
            ok += 1
            if ok >= 3:
                break
        else:
            print(f"FAIL {celex} | status={r.status_code} | len={len(r.text)}")
    except Exception as e:
        print(f"ERR  {celex}: {e}")
    tested += 1
    if tested >= 15:
        break

print(f"\nRésultat: {ok} OK sur {tested} testés")
