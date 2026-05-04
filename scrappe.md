# Systeme de Scraping Lexavo — Configuration et Procedures

## Architecture

```
base-juridique-app/
  orchestrator.py          — Lance, surveille, redemarre les scrapers automatiquement
  config.py                — Configuration globale (delays, limites, chemins)
  scrapers/                — 23 scrapers (1 par source)
  output/                  — JSON bruts par source
  output/normalized/       — JSON normalises (schema uniforme)
  logs/                    — 1 fichier log par scraper + orchestrator.log
  utils/normalize_schema.py — Normaliseur universel
  processors/cleaner.py    — Nettoyage des donnees
  rag/indexer.py           — Indexation Qdrant
```

---

## Schema JSON uniforme (6 champs obligatoires)

Chaque document normalise DOIT contenir :

```json
{
  "doc_id": "CE_200114",
  "source": "Conseil d'Etat",
  "title": "Arret n 200114 — Conseil d'Etat belge",
  "full_text": "... texte complet et entier ...",
  "date": "2010-01-27",
  "url": "https://www.raadvst-consetat.be/Arrets/200000/100/200114.pdf"
}
```

### Mapping par source (fichiers bruts → normalises)

| Source | Identifiant | Date | Titre | Texte | URL |
|--------|-------------|------|-------|-------|-----|
| apd, bruxelles, cbe, ccrek, chambre, cnt, consconst, conseil_etat, datagov, gallilex | `doc_id` | `date` | `title` | `full_text` | `url` (ou `pdf_url`) |
| eurlex | `celex` → `doc_id` | `date` | `title` (si vide: "EUR-Lex {celex}") | `full_text` | `url` |
| juridat | `ecli` → `doc_id` | `date` | `title` (si vide: "JuPortal {ecli}") | `full_text` | `url` |
| hudoc | `item_id` → `doc_id` | `metadata.kpdate` → `date` | `metadata.docname` → `title` | `full_text` | `url` |
| justel | `numac` → `doc_id` | `date_publication` → `date` | `title` | `full_text` | `url` |
| moniteur | `numac` → `doc_id` | `date_publication` → `date` | `title` | `full_text` | `url` |
| codex_vlaanderen | `uri` → `doc_id` | `date` | `title` | `parts[]` concatenes → `full_text` | `expression_url` → `url` |
| wallex | `doc_id` | `date` | `title` | `articles[].texte` concatenes → `full_text` | `url` |
| cce | `doc_id` | `date` (extraite du texte FR/NL) | `title` | `full_text` | `url` |

---

## Orchestrateur (orchestrator.py)

### Fonctionnement

1. Lance tous les scrapers configures comme sous-processus Python
2. Verifie chaque processus toutes les **30 secondes**
3. Redemarre automatiquement tout scraper qui meurt (code retour != 0)
4. Compte les documents dans output/ toutes les **5 minutes**
5. Log dans `logs/orchestrator.log`
6. Utilise `CREATE_NO_WINDOW` pour resister a la fermeture du terminal Windows
7. Arret propre sur Ctrl+C (termine tous les enfants)

### Configuration des scrapers

Modifier la liste `SCRAPERS` dans orchestrator.py pour chaque vague :

```python
# VAGUE 1+2 exemple :
SCRAPERS = [
    {"script": "scrapers/moniteur_scraper.py",       "args": ["--max", "300000"]},
    {"script": "scrapers/conseil_etat_async.py",     "args": ["--start", "200000", "--end", "270000", "--concurrency", "10"]},
    {"script": "scrapers/cce_scraper.py",            "args": ["--max-docs", "100000"]},
    {"script": "scrapers/juportal_scraper.py",       "args": ["--max-docs", "100000"]},
]
```

### Lancement

```bash
# Via PowerShell (reste actif meme si le terminal bash ferme)
powershell.exe -Command "Start-Process -FilePath 'python' -ArgumentList 'orchestrator.py' -WorkingDirectory 'C:\Users\bahma\Downloads\base-juridique-app' -WindowStyle Minimized"

# Ou via le script .bat (ouvre sa propre fenetre)
start_orchestrator.bat
```

### Anti-veille Windows

```powershell
powercfg -change -standby-timeout-ac 0
powercfg -change -monitor-timeout-ac 0
powercfg -change -hibernate-timeout-ac 0
```

---

## Strategie : Approche Hybride Priorisee

**Principe** : 2-3 scrapers max en parallele, du plus gros volume au plus petit, validation V1-V5 avant de passer a la vague suivante.

### Vagues d'execution

| Vague | Sources | Volume cible | Statut |
|-------|---------|-------------|--------|
| 1+2 | Moniteur (300K) + CE async (250K) + CCE (100K) + JuPortal (100K) | 750K | EN COURS |
| 3 | Codex VL SPARQL (50K) + GalliLex (13K) + WalLex (5K) | 68K | En attente |
| 4 | EUR-Lex extension (150K) + HUDOC (841) + Bruxelles (3K) | 154K | En attente |
| 5 | Chambre (5K) + CCREK (447) + CNT (370) + APD (198) + ConsConst (5.4K) + Justel (50K) + FSMA (241) | 62K | En attente |
| 6 | Re-indexation globale + 10 verifications finales | — | En attente |

---

## 5 Regles d'Or — A RESPECTER TOUJOURS

### 1. ZERO INVENTION
Ne jamais fabriquer un document, un article de loi, une decision de justice.
Chaque document doit avoir une URL source verifiable.
Si la source n'existe pas → SKIP.

### 2. TEXTE COMPLET ET ENTIER
Ne jamais tronquer, resumer, ou reformuler un texte juridique.
Le texte doit etre reproduit mot pour mot tel qu'il apparait sur la source officielle.
Si le texte est tronque → re-scraper avec un outil different.

### 3. VERIFICATION LEGALE
Avant de scraper une source, verifier :
- Est-ce un acte officiel de l'autorite ? (art. XI.172 §2 CDE)
- Les CGU autorisent-elles la reutilisation ?
- La licence est-elle ouverte (CC-0, CC-BY) ?
Si NON a toutes ces questions → NE PAS SCRAPER.

### 4. PROTOCOLE D'INDEXATION
a. Scrape → JSON brut dans `output/{source}/`
b. Normalisation → `utils/normalize_schema.py` → `output/normalized/`
c. Validation → 10 verifications (voir ci-dessous)
d. Indexation → Qdrant via `rag/indexer.py`
e. Verification RAG → 5 requetes de test

### 5. RESPECT DES SERVEURS
- Delay minimum 1.5s entre requetes (2.0s pour le Moniteur)
- Respecter robots.txt
- Ne pas surcharger les serveurs publics belges
- Si rate limited → augmenter le delay, ne PAS contourner

---

## 10 Verifications Obligatoires

Executer TOUTES ces verifications apres chaque vague, sans exception.

### R1 — Zero Invention
- Lire 5 fichiers JSON recents de 5 sources differentes
- Verifier que chaque URL commence par `https://` et pointe vers un site gouvernemental officiel
- Verifier que chaque doc_id correspond a un vrai numero de decision/loi
- Verifier qu'aucun full_text ne contient de texte invente (pas de "Lorem ipsum", pas de texte generique)

### R2 — Texte Complet et Entier
- Pour les 5 fichiers : verifier que `full_text` > 500 caracteres
- Verifier que le texte se termine par une phrase complete (signatures, mentions de cloture — pas tronque)
- Verifier que le texte contient du vocabulaire juridique (loi, article, arrete, tribunal, constitution, code)

### R3 — Verification Legale
- Confirmer que toutes les sources scrapees sont des actes officiels de l'autorite (art. XI.172 §2 CDE)
- Liste des sources autorisees :
  - Moniteur belge, Conseil d'Etat, Cour constitutionnelle, CCE, JuPortal
  - EUR-Lex, HUDOC, Codex Vlaanderen, GalliLex, WalLex, Bruxelles
  - FSMA, CCREK, APD, CNT, Chambre, DataGov, CBE, Justel
- Source INTERDITE : doctrine (protegee par droit d'auteur, art. XI.165 CDE)

### R4 — Protocole d'Indexation
- Verifier que `output/` contient les JSON bruts organises par source
- Verifier que `output/normalized/` contient les fichiers normalises
- Compter les fichiers dans chaque dossier — le total normalise doit correspondre au total brut
- Verifier que chaque fichier normalise contient exactement les 6 champs obligatoires

### R5 — Respect des Serveurs
- Lire les 20 dernieres lignes de chaque log dans `logs/`
- Verifier qu'il n'y a pas de flood (pas de 429 en masse sans backoff)
- Verifier qu'aucun serveur n'a banni l'IP (pas de 403 permanents)
- Confirmer que les delays configures sont respectes

### T1 — Processus Actifs
- `tasklist | grep python` pour compter les processus Python
- Verifier que l'orchestrateur tourne (derniere ligne de `logs/orchestrator.log`)
- Verifier que les scrapers produisent de nouveaux fichiers (fichiers recents dans output/)

### T2 — Dates Correctes
- Pour les 5 fichiers : date au format YYYY-MM-DD
- Annee entre 1830 et 2026 (dates realistes pour le droit belge)
- Verifier que `date_promulgation` du Moniteur n'est PAS la date du scraping
- Verifier que le CCE a une date extraite du texte (FR ou NL)

### T3 — Pas de HTML Residuel
- Pour les 5 fichiers : verifier absence de `<div>`, `<p>`, `<script>`, `<style>`, `<span>`, `<table>`, `<a href=` dans `full_text`

### T4 — Encodage UTF-8
- Verifier absence de caracteres corrompus : Ã©, Â, ï¿½, \u0000
- Les accents francais (e, e, a, u, c) doivent etre correctement encodes

### T5 — Pas de Doublons
- Verifier que les doc_id sont uniques dans chaque source
- `find output/{source}/ -name "*.json" | wc -l` doit correspondre au nombre de doc_id distincts

---

## 10 Verifications PAR SCRAPER (a executer pour chaque scraper individuellement)

Ces verifications s'appliquent a CHAQUE scraper, pas globalement. Si un seul echoue → le scraper est considere comme defaillant.

### S1 — Processus Vivant
- Verifier que le processus Python du scraper est actif : `tasklist | grep -i python`
- Verifier dans `logs/{scraper}.log` que la derniere ligne date de < 5 minutes
- Si le log est silencieux depuis > 10 minutes → scraper bloque ou mort

### S2 — Production Active (CRITIQUE)
- Comparer le nombre de fichiers JSON maintenant vs il y a 10 minutes
- `find output/{source}/ -name "*.json" -newer /tmp/marker | wc -l` (creer marker avec `touch -d '10 minutes ago' /tmp/marker`)
- Si 0 nouveaux fichiers en 10 minutes et scraper non termine → PROBLEME
- C'est cette verification qui manquait pour CCE et JuPortal

### S3 — Debit (Throughput)
- Calculer le nombre de docs/heure : `(total_docs / heures_ecoulees)`
- Comparer au debit attendu :
  - Moniteur : ~1800 docs/h (delay 2.0s)
  - CE async : ~7200 docs/h (10 connexions, delay 0.5s)
  - CCE : ~3600 docs/h (delay 0.4s, 4 URL variantes)
  - JuPortal : ~900 docs/h (delay 0.4s, CSRF overhead)
- Si debit < 50% de l'attendu → investiguer

### S4 — Erreurs dans les Logs
- `grep -ic "error\|exception\|traceback\|failed" logs/{scraper}.log`
- `grep -ic "429\|403\|500\|502\|503" logs/{scraper}.log`
- Taux d'erreur acceptable : < 5% des requetes
- Si > 20% d'erreurs → STOP et corriger avant de continuer
- Verifier absence de boucles infinies (meme erreur repetee 100+ fois)

### S5 — Checkpoint Progression
- Lire le fichier `.checkpoint` du scraper (s'il en a un)
- Verifier que le checkpoint avance entre 2 verifications
- CE : `cat output/conseil_etat/.checkpoint` → doit augmenter
- Moniteur : verifier l'annee en cours dans les logs
- Si checkpoint identique apres 15 minutes → scraper bloque

### S6 — Qualite des 5 Derniers Documents
- Lire les 5 fichiers JSON les plus recents du scraper
- Verifier que `full_text` > 500 caracteres
- Verifier que `date` est au format YYYY-MM-DD et annee 1830-2026
- Verifier que `doc_id` est non-vide et unique
- Verifier que `url` commence par `https://`
- Verifier absence de HTML residuel dans `full_text`

### S7 — Pas de Repetition (Anti-boucle)
- Verifier que les 10 derniers `doc_id` sont tous differents
- Verifier que les 10 derniers `full_text` ne sont pas identiques
- Si un scraper re-telecharge les memes documents en boucle → BUG
- JuPortal avait exactement ce probleme (toujours les memes 100 resultats)

### S8 — Respect du Delay
- Lire les timestamps dans les logs : calculer l'ecart entre requetes consecutives
- Moniteur : ecart >= 2.0s obligatoire
- CE async : ecart >= 0.5s par connexion
- Autres : ecart >= delay configure dans config.py
- Si ecart < delay → risque de ban IP, corriger immediatement

### S9 — Espace Disque et Memoire
- `df -h .` → espace disque restant > 5 GB
- Taille moyenne d'un JSON par source :
  - Moniteur : ~15 KB/doc → 300K docs = ~4.5 GB
  - CE : ~8 KB/doc → 250K docs = ~2 GB
- Si memoire RAM > 2 GB pour un scraper → fuite memoire probable
- Verifier avec `tasklist /FI "PID eq {pid}" /FO CSV` la memoire du processus

### S10 — Test de Bout en Bout (Smoke Test)
- Pour chaque scraper, ouvrir l'URL du dernier document telecharge dans un navigateur
- Verifier que la page existe et contient du texte juridique
- Comparer visuellement les 200 premiers caracteres du `full_text` avec la source
- Si le texte ne correspond pas → scraper corrompu, STOP immediat

### Commandes de verification par scraper

```bash
# === MONITEUR ===
echo "=== MONITEUR ===" && \
count=$(find output/moniteur/ -name "*.json" 2>/dev/null | wc -l) && \
recent=$(find output/moniteur/ -name "*.json" -newermt '10 minutes ago' 2>/dev/null | wc -l) && \
errors=$(grep -ic "error\|429\|403" logs/moniteur_scraper.log 2>/dev/null || echo 0) && \
echo "Total: $count | Nouveaux (10min): $recent | Erreurs: $errors" && \
tail -3 logs/moniteur_scraper.log

# === CONSEIL D'ETAT ===
echo "=== CONSEIL D'ETAT ===" && \
count=$(find output/conseil_etat/ -name "*.json" 2>/dev/null | wc -l) && \
recent=$(find output/conseil_etat/ -name "*.json" -newermt '10 minutes ago' 2>/dev/null | wc -l) && \
checkpoint=$(cat output/conseil_etat/.checkpoint 2>/dev/null || echo "N/A") && \
echo "Total: $count | Nouveaux (10min): $recent | Checkpoint: $checkpoint" && \
tail -3 logs/conseil_etat_async.log

# === CCE ===
echo "=== CCE ===" && \
count=$(find output/cce/ -name "*.json" 2>/dev/null | wc -l) && \
recent=$(find output/cce/ -name "*.json" -newermt '10 minutes ago' 2>/dev/null | wc -l) && \
echo "Total: $count | Nouveaux (10min): $recent" && \
tail -3 logs/cce_scraper.log

# === JUPORTAL ===
echo "=== JUPORTAL ===" && \
count=$(find output/juportal/ -name "*.json" 2>/dev/null | wc -l) && \
recent=$(find output/juportal/ -name "*.json" -newermt '10 minutes ago' 2>/dev/null | wc -l) && \
echo "Total: $count | Nouveaux (10min): $recent" && \
tail -3 logs/juportal_scraper.log

# === VERIFICATION QUALITE DERNIER DOC (toute source) ===
# Usage : bash verify_last.sh {source}
# Exemple : bash verify_last.sh moniteur
SOURCE=$1
LAST=$(ls -t output/$SOURCE/*.json 2>/dev/null | head -1)
if [ -n "$LAST" ]; then
  python -c "
import json
d=json.load(open('$LAST',encoding='utf-8'))
checks = []
checks.append(('doc_id', bool(d.get('doc_id'))))
checks.append(('full_text>500', len(d.get('full_text',''))>500))
checks.append(('date format', bool(d.get('date','')) and len(d.get('date',''))==10))
checks.append(('url https', d.get('url','').startswith('https://')))
checks.append(('no HTML', '<div>' not in d.get('full_text','') and '<p>' not in d.get('full_text','')))
for name, ok in checks:
    print(f'  {\"OK\" if ok else \"FAIL\"} {name}')
print(f'  Fichier: {\"$LAST\"}')
"
else
  echo "  Aucun fichier trouve pour $SOURCE"
fi
```

---

## Commandes de Verification Rapide

```bash
# Processus actifs
tasklist | grep -ic python

# Comptage par source
for d in output/*/; do name=$(basename "$d"); count=$(find "$d" -maxdepth 1 -name "*.json" | wc -l); [ "$count" -gt 0 ] && printf "%7d %s\n" "$count" "$name"; done | sort -rn

# Dernier checkpoint CE
cat output/conseil_etat/.checkpoint

# Derniers logs
tail -5 logs/orchestrator.log
tail -5 logs/moniteur_scraper.log
tail -5 logs/conseil_etat_async.log

# Verifier un fichier JSON
python -c "import json; d=json.load(open('output/moniteur/FICHIER.json',encoding='utf-8')); print('date_prom:', d.get('date_promulgation','')); print('title:', d.get('title','')[:70]); print('full_text len:', len(d.get('full_text','')))"

# Relancer l'orchestrateur
powershell.exe -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force"
sleep 3
powershell.exe -Command "Start-Process -FilePath 'python' -ArgumentList 'orchestrator.py' -WorkingDirectory 'C:\Users\bahma\Downloads\base-juridique-app' -WindowStyle Minimized"

# Normaliser les nouveaux fichiers
cd base-juridique-app && python utils/normalize_schema.py
```

---

## Autocorrection par Scraper Defaillant + 5 Verifications Post-Correction

Quand un scraper echoue a une verification S1-S10, appliquer la procedure d'autocorrection ci-dessous PUIS les 5 verifications de confirmation.

---

### MONITEUR — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 nouveaux docs (S2) | Rate limited (429 en masse) | Augmenter `MONITEUR_DELAY` a 3.0s, relancer |
| Erreurs 429 > 20% (S4) | Serveur surcharge | Backoff exponentiel : 5s → 10s → 15s → pause 60s |
| date_promulgation = date du jour | Regex cherche dans le header page | Forcer extraction depuis `doc["title"]` APRES ajout du titre (ligne 403+) |
| full_text < 500 chars | PDF pre-1997 non extrait | Fallback pdfplumber → docling OCR → skip si echec |
| HTML residuel dans full_text | Parser BS4 incomplet | Passer full_text dans `re.sub(r'<[^>]+>', '', text)` avant sauvegarde |
| Processus mort (S1) | Crash memoire sur gros PDF | Ajouter try/except autour de parse_article, logger et continuer |
| Checkpoint stagne (S5) | Page HTML changee, selecteurs CSS casses | Verifier structure HTML manuellement, adapter les selecteurs |

**5 Verifications Post-Correction Moniteur :**
1. Relancer le scraper en mode test (`--max 10`) → doit produire 10 docs valides
2. Verifier que les 10 docs ont `date_promulgation` != date du jour (2026-xx-xx)
3. Verifier que `full_text` > 500 chars pour les 10 docs
4. Verifier absence de `<div>`, `<p>`, `<script>` dans full_text
5. Comparer 1 doc mot pour mot avec la source web originale (ouvrir URL)

---

### CONSEIL D'ETAT — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 nouveaux docs (S2) | Plage de numeros epuisee (404) | Verifier `.checkpoint`, sauter les plages vides, etendre `--end` |
| Checkpoint stagne (S5) | Tous les numeros du batch sont 404 | Augmenter `batch_size` a 500 pour traverser les trous plus vite |
| Erreurs pdfplumber (S4) | PDF corrompu ou scan image | Fallback : `pymupdf4llm` → `docling` OCR → skip |
| full_text vide (S6) | PDF image sans couche texte | Utiliser OCR (docling) sur le PDF |
| Date vide (S6) | Regex ne matche pas le format de l'arret | Etendre regex : chercher aussi format `dd/mm/yyyy` et `dd.mm.yyyy` |
| Debit < 3600 docs/h (S3) | Trop de 404 dans la plage | Sauter par blocs de 1000 quand > 90% de 404 consecutifs |
| Connexion timeout | Serveur CE lent | Reduire `--concurrency` a 5, augmenter timeout a 120s |

**5 Verifications Post-Correction CE :**
1. Relancer sur une plage de 50 numeros connus (`--start 260000 --end 260050`) → doit produire > 10 docs
2. Verifier que le checkpoint avance apres 2 batches
3. Verifier que les PDFs extraits ont `full_text` > 200 chars
4. Verifier que `date` est extraite pour > 80% des docs (format YYYY-MM-DD)
5. Ouvrir 1 URL PDF dans le navigateur, comparer avec le `full_text` extrait

---

### CCE — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 nouveaux docs (S2) | Phase de collecte des numeros (pas encore en download) | Verifier logs : si "collecte" → normal, attendre. Si "download" et 0 → BUG |
| full_text vide (S6) | Aucune des 4 variantes URL PDF ne marche | Ajouter 5e variante URL, ou scraper la page HTML directe |
| Date vide (S6) | Regex FR+NL ne matche pas | Etendre recherche a 3000 premiers chars, ajouter format numerique dd/mm/yyyy |
| Boucle repetition (S7) | Re-telecharge les memes numeros | Verifier le fichier de tracking des numeros deja traites |
| Erreurs 403 (S4) | IP bannie temporairement | Pause 30 minutes, puis reprendre avec delay 1.0s |
| Selecteurs CSS casses | Site CCE a change sa structure | Inspecter la page manuellement, adapter les selecteurs dans le scraper |
| Debit < 1000 docs/h (S3) | 4 variantes URL testees pour chaque doc | Tester la variante la plus probable en premier (optimiser l'ordre) |

**5 Verifications Post-Correction CCE :**
1. Tester 10 numeros CCE connus → doit telecharger et extraire le texte de > 7/10
2. Verifier que `date` est extraite (FR ou NL) pour > 70% des docs
3. Verifier que `full_text` contient des mots juridiques (tribunal, arret, recours, vreemdeling)
4. Verifier que le tracking de numeros empeche les re-telechargements (S7)
5. Comparer 1 arret avec la source PDF originale (mot pour mot)

---

### JUPORTAL — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 nouveaux docs (S2) | Retourne toujours les memes 100 resultats | Segmenter par juridiction (7 codes) au lieu de par annee |
| Boucle repetition (S7) | Memes ECLI a chaque requete | Verifier deduplication par ECLI, varier les mots-cles et juridictions |
| CSRF token expire (S4) | Session expiree | Re-fetch le formulaire pour obtenir un nouveau token CSRF |
| Erreurs 403 (S4) | Trop de requetes rapides | Augmenter delay a 1.0s, espacer les sessions |
| full_text vide (S6) | Page de detail ne contient pas le texte complet | Parser le lien PDF dans la page de detail, extraire avec pdfplumber |
| Debit < 500 docs/h (S3) | Overhead CSRF + pagination | Garder la session ouverte, reutiliser le token tant qu'il est valide |
| Pagination bloquee | Lien "suivant" change de format | Adapter regex de detection du lien suivant (PAGE=, page=, p=) |

**5 Verifications Post-Correction JuPortal :**
1. Lancer avec 3 mots-cles differents → doit retourner des ECLI differents pour chaque
2. Verifier que la pagination fonctionne : page 1 et page 2 ont des resultats differents
3. Verifier que > 50% des docs ont `full_text` > 500 chars
4. Verifier que les 7 juridictions retournent chacune au moins 1 resultat
5. Comparer 1 document JuPortal avec la source web originale

---

### CONSCONST — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 nouveaux docs (S2) | Range d'annees epuise ou PDFs manquants | Verifier annee en cours dans les logs, etendre la plage |
| Erreur httpx Unicode | User-Agent contient des accents | Supprimer tous les accents du User-Agent string |
| full_text vide (S6) | PDF image (vieux arrets) | Fallback OCR avec docling |
| Date vide (S6) | Format de date inhabituel dans l'arret | Ajouter regex pour "Arret n° X/YYYY" → extraire YYYY |
| Processus mort (S1) | Async event loop crash | Relancer avec `--concurrency 5` au lieu de 10 |

**5 Verifications Post-Correction ConsConst :**
1. Tester annee 2024 → doit trouver > 50 arrets
2. Verifier format doc_id : `CC_YYYY_NNN`
3. Verifier que `full_text` contient "Cour constitutionnelle" ou "Grondwettelijk Hof"
4. Verifier que `date` correspond a l'annee du doc_id
5. Ouvrir 1 URL dans le navigateur, confirmer que le PDF existe

---

### GALLILEX — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 nouveaux docs (S2) | Pagination cassee ou fin de catalogue | Verifier page actuelle vs total pages dans les logs |
| Erreurs 500 (S4) | Serveur GalliLex instable | Retry avec backoff 5s/10s/30s, max 3 tentatives |
| full_text tronque (S6) | Texte coupe a la pagination HTML | Concatener toutes les pages du document |
| Doublons (S7) | Meme doc liste sur plusieurs pages | Deduplication stricte par doc_id |

**5 Verifications Post-Correction GalliLex :**
1. Verifier que la page suivante retourne des resultats differents de la page actuelle
2. Verifier `full_text` > 500 chars pour les 5 derniers docs
3. Verifier que `url` pointe vers gallilex.cfwb.be
4. Verifier absence de HTML residuel
5. Comparer 1 doc avec la source originale

---

### WALLEX — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 resultats (S2) | Endpoint GET au lieu de POST | Utiliser AJAX POST vers le bon endpoint (deja corrige) |
| articles[] vide (S6) | Structure JSON changee | Inspecter la reponse brute, adapter le parsing |
| full_text = concatenation vide | Articles sans champ `texte` | Fallback : chercher champ `contenu`, `content`, `body` |

**5 Verifications Post-Correction WalLex :**
1. Envoyer 1 requete POST → doit retourner > 0 resultats
2. Verifier que `articles[]` contient du texte pour > 80% des docs
3. Verifier que `full_text` concatene > 500 chars
4. Verifier que `url` pointe vers wallex.wallonie.be
5. Comparer 1 doc avec la source originale

---

### HUDOC — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 nouveaux docs (S2) | API HUDOC a change son format | Verifier la documentation API officielle CEDH |
| full_text vide (S6) | Texte dans un champ different | Chercher dans `content`, `body`, `text`, `documentcollection2` |
| metadata manquantes | Champs renommes | Mapper les nouveaux noms de champs |

**5 Verifications Post-Correction HUDOC :**
1. Requete API avec 1 item_id connu → doit retourner le document complet
2. Verifier que `metadata.kpdate` est parsee en YYYY-MM-DD
3. Verifier que `full_text` contient "EUROPEAN COURT" ou "COUR EUROPEENNE"
4. Verifier que `url` pointe vers hudoc.echr.coe.int
5. Comparer 1 arret avec la version PDF officielle

---

### CODEX VLAANDEREN — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 resultats SPARQL (S2) | Endpoint SPARQL down ou change | Fallback vers API REST (deja implemente) |
| parts[] vide (S6) | Structure de reponse changee | Inspecter la reponse, adapter le parsing |
| Timeout SPARQL (S4) | Requete trop large | Reduire LIMIT a 500, paginer avec OFFSET |

**5 Verifications Post-Correction Codex VL :**
1. Envoyer 1 requete SPARQL simple → doit retourner > 0 resultats
2. Si SPARQL echoue, verifier que le fallback REST fonctionne
3. Verifier que `parts[]` concatene donne `full_text` > 500 chars
4. Verifier que `expression_url` est une URL valide
5. Ouvrir 1 URL dans le navigateur, confirmer le texte

---

### EURLEX — Autocorrection

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 nouveaux docs (S2) | Necessite EU Login pour bulk | Utiliser SPARQL API publique (cellar.ec.europa.eu) |
| full_text vide (S6) | Document disponible uniquement en PDF | Telecharger le PDF, extraire avec pdfplumber |
| celex invalide (S6) | Format CELEX change | Adapter regex de validation CELEX |
| Titre vide | Pas de titre dans les metadonnees | Generer titre : "EUR-Lex {celex}" |

**5 Verifications Post-Correction EUR-Lex :**
1. Requete SPARQL pour 10 CELEX recents → doit retourner les documents
2. Verifier que `full_text` > 500 chars pour > 80% des docs
3. Verifier que `celex` → `doc_id` est correctement mappe
4. Verifier que `url` pointe vers eur-lex.europa.eu
5. Comparer 1 document avec la version officielle EUR-Lex

---

### CHAMBRE / CCREK / CNT / APD / FSMA / CBE / DATAGOV / JUSTEL / BRUXELLES — Autocorrection generique (petits volumes)

| Symptome | Diagnostic | Correction automatique |
|----------|-----------|----------------------|
| 0 resultats (S2) | URL ou endpoint change | Verifier manuellement le site, adapter l'URL |
| Erreurs 403 (S4) | Changement de politique d'acces | Verifier robots.txt et CGU, ajouter User-Agent correct |
| full_text vide (S6) | Structure HTML changee | Inspecter la page, adapter les selecteurs CSS/XPath |
| Processus mort (S1) | Exception non geree | Ajouter try/except global, logger l'erreur, continuer |

**5 Verifications Post-Correction (generiques) :**
1. Tester 5 URLs connues → doit telecharger et parser correctement
2. Verifier que les 6 champs obligatoires sont presents et non-vides
3. Verifier que `full_text` > 200 chars (certaines sources ont des textes courts)
4. Verifier absence de HTML residuel
5. Comparer 1 doc avec la source originale

---

### Procedure d'autocorrection unifiee (flowchart)

```
Verification S1-S10 echoue pour scraper X
         |
         v
Identifier le symptome exact (quel Sx a echoue)
         |
         v
Consulter la table d'autocorrection du scraper X ci-dessus
         |
         v
Appliquer la correction automatique indiquee
         |
         v
Executer les 5 verifications post-correction du scraper X
         |
    +----+----+
    |         |
  5/5 OK    < 5/5 OK
    |         |
    v         v
Reprendre   Correction manuelle requise :
le scrape   1. Lire les logs complets
            2. Inspecter la source web manuellement
            3. Adapter le code du scraper
            4. Re-tester avec --max 10
            5. Si toujours KO → SKIP cette source, passer a la suivante
```

---

## Scrapers et leurs specificites

| Scraper | Fichier | Delay | Particularite |
|---------|---------|-------|---------------|
| Moniteur belge | `moniteur_scraper.py` | 2.0s | Backoff 429 (5s/10s/15s). Textes pre-1997 = PDF only |
| Conseil d'Etat | `conseil_etat_async.py` | 0.5s | Async 10 connexions. PDFs par numero (200000→270000) |
| ConsConst | `scrape_consconst_fast.py` | 0.3s | Async httpx. PDFs par annee (1985→2026) |
| CCE | `cce_scraper.py` | 0.4s | 4 variantes URL PDF. Dates extraites FR+NL du texte |
| JuPortal | `juportal_scraper.py` | 0.4s | CSRF token requis. Limite 100 resultats par requete |
| GalliLex | `gallilex_scraper.py` | 0.4s | Pagination standard |
| WalLex | `wallex_scraper.py` | 0.4s | AJAX POST endpoint. Texte dans `articles[]` |
| HUDOC | `hudoc_scraper.py` | 0.4s | API officielle CEDH |
| Codex VL | `codex_sparql_scraper.py` | 1.0s | SPARQL ou API REST fallback |
| EUR-Lex | `eurlex_scraper.py` | 0.4s | Bulk download officiel recommande |

---

## Bugs Corriges (Reference)

1. **CCE dates vides** : regex etendue aux mois FR + NL, recherche dans 2000 premiers chars
2. **Moniteur date_promulgation = date du scraping** : fallback cherchait dans le header de page (date du jour). Corrige pour chercher dans le titre du document
3. **Moniteur titre ajoute apres extraction date** : date extraite du titre APRES son ajout (ligne 403+), pas dans parse_article ou le titre est encore vide
4. **ConsConst Unicode User-Agent** : caractere `e` dans "academique" rejecte par httpx. Accent supprime
5. **WalLex 0 resultats** : GET retournait la homepage. Endpoint AJAX POST decouvert
6. **Juridat 404** : site migre vers JuPortal depuis 2020. URLs mises a jour
7. **JuPortal typo** : champ formulaire `TRECHLANGNI` → `TRECHLANGNL`

---

## Objectif Final

| Metrique | Valeur |
|----------|--------|
| Documents cibles | ~1,700,000 |
| Documents actuels | ~128,000 (en croissance) |
| Sources | 19 sources officielles |
| Strategie | Hybride priorisee, 6 vagues |
| Verification | 10 points obligatoires par vague |
| Indexation | Qdrant (paraphrase-multilingual-MiniLM-L12-v2, 384 dim) |
