# Lexavo Audience Analysis

Valide la demande pour chaque feature Lexavo avant de construire.

## Usage

```bash
# Mode mock (demo, sans API)
python scripts/audience_analysis.py --mock

# Mode reel (necessite APIFY_API_KEY dans .env)
python scripts/audience_analysis.py --live

# Generer rapport HTML
python scripts/audience_analysis.py --report
```

## Output

- Console : rapport structure avec scores
- `output/audience_analysis_report.html` : rapport visuel
- `output/audience_analysis_report.json` : donnees brutes

## Features scorees

| Feature | Score | Volume mensuel |
|---------|-------|----------------|
| lexavo-match | 9.5 | 12,400 |
| lexavo-calculateurs | 9.2 | 8,700 |
| lexavo-fiscal | 8.1 | 4,500 |
| lexavo-shield | 7.8 | 3,200 |
| lexavo-heritage | 7.6 | 3,200 |
| lexavo-compliance | 7.4 | 1,200 |
| lexavo-litiges | 7.3 | 1,890 |
| lexavo-diagnostic | 6.8 | 2,100 |
| lexavo-emergency | 6.2 | 890 |
| lexavo-alertes | 5.9 | 430 |

## Sources analysees

1. **Google Autocomplete Belgium** — 10 seed queries x 10 suggestions
2. **Reddit r/belgium** — Posts juridiques (score >= 10, 12 derniers mois)
3. **Google People Also Ask** — Variations par feature
4. **Keyword volumes** — 30 mots-cles avec volumes estimes
5. **Feature demand scoring** — Score 1-10 par feature Lexavo

## Variables d'environnement

```
APIFY_API_KEY=your_key_here   # ou APIFY_TOKEN
```

Cree un fichier `.env` a la racine du projet avec la cle Apify.
Sans cle, le script tourne automatiquement en mode mock.
