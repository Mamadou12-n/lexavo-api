---
name: add-legal-source
description: Ajouter une nouvelle source juridique belge a la base ChromaDB Lexavo — processus obligatoire en 8 etapes
---

# Skill : Ajouter une source juridique a Lexavo

## Regles absolues
- **Zero invention** : URL, NUMAC, cn = verifies sur source officielle (ejustice, eTAAMB, SPF)
- **Texte complet** : jamais partiel, toujours le document entier
- **Verifier 2 fois** : chaque etape est verifiee avant de passer a la suivante

## Processus obligatoire (8 etapes)

### Etape 1 — VERIFIER la source
- URL officielle uniquement (ejustice.just.fgov.be, eTAAMB, finances.belgium.be, emploi.belgique.be)
- Pas d'URL inventee — tester avec `requests.get()` et verifier HTTP 200
- Si NUMAC : verifier sur eTAAMB.openjustice.be
- Si cn JUSTEL : verifier via `cgi_loi/change_lg.pl?cn={cn}`

### Etape 2 — TESTER l'accessibilite
```python
r = requests.get(url, headers=HEADERS, timeout=20)
assert r.status_code == 200, f"HTTP {r.status_code}"
assert len(r.text) > 1000, f"Contenu trop court ({len(r.text)} chars)"
assert "Desole" not in r.text[:500], "Page d'erreur JUSTEL"
assert "Aide ELI" not in r.text[:200], "Page d'erreur ELI"
```

### Etape 3 — SCRAPER le contenu
- Calquer sur `scrapers/justel_scraper.py` (codes via change_lg.pl) ou `scrapers/thematic_scraper.py` (pages SPF)
- Format de sortie : JSON dans `output/justel/` avec champs obligatoires :
  ```json
  {
    "source": "JUSTEL|SPF Finances|SPF Emploi|...",
    "doc_id": "identifiant_unique",
    "title": "Titre complet",
    "full_text": "texte integral",
    "char_count": 12345,
    "url": "URL source officielle"
  }
  ```

### Etape 4 — VERIFIER le contenu scrape
```python
# Pas de page d'erreur
assert "Aide ELI" not in text[:200]
assert "Desole" not in text[:500]
# Contenu juridique reel
legal_kw = ["article", "loi", "alinea", "paragraphe", "disposition"]
assert sum(1 for kw in legal_kw if kw in text.lower()) >= 2
```

### Etape 5 — NORMALISER via processors/cleaner.py
```bash
python -c "from processors.cleaner import process_all_sources; process_all_sources()"
```

### Etape 6 — INDEXER via rag/indexer.py
```bash
python -c "
from rag.indexer import build_index
from config import OUTPUT_DIR
build_index(normalized_dir=OUTPUT_DIR/'normalized', chroma_dir=OUTPUT_DIR/'chroma_db', reset=True)
"
```
- Chunks 1500 chars pour codes, 512 pour jurisprudence
- Alt.8 index articles construit automatiquement

### Etape 7 — TESTER le RAG (3 questions minimum)
```python
from rag.retriever import retrieve
# Question 1 : avec numero d'article
chunks = retrieve("article X du [code]")
assert any("[code]" in c["title"].lower() for c in chunks[:3])

# Question 2 : sans numero d'article
chunks = retrieve("[terme juridique] [code]")
assert len(chunks) > 0 and chunks[0]["score"] > 0.5

# Question 3 : verification contenu
assert "[texte attendu]" in chunks[0]["chunk_text"].lower()
```

### Etape 8 — DEPLOYER
```bash
# Commit
git add scrapers/ rag/ run_all.py
git commit -m "feat: ajout source [nom]"
git push origin main

# Re-upload ChromaDB release
tar -czf /tmp/chroma_db_v2.tar.gz -C output chroma_db
gh release delete v2.0-chroma --yes
gh release create v2.0-chroma --title "ChromaDB updated" /tmp/chroma_db_v2.tar.gz
```

## Checklist finale
- [ ] URL source officielle verifiee (HTTP 200)
- [ ] NUMAC/cn verifie sur eTAAMB (si applicable)
- [ ] Contenu complet (pas tronque, pas page d'erreur)
- [ ] Normalisation OK
- [ ] Indexation OK (chunks + articles)
- [ ] 3 questions RAG repondues correctement
- [ ] Commit + push + release ChromaDB
