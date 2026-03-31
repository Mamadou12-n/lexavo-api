---
name: lexavo-decode
description: >
  Traduit des documents administratifs belges en langage clair et actionnable.
  Déclencher pour : décoder une lettre recommandée, un jugement, un avis d'imposition,
  une décision administrative, un contrat en néerlandais, un document SPF.
  Supporte PDF, images (OCR) et texte brut. Langues : FR, NL, EN.
category: lexavo
risk: safe
tags: "[decode, traduction, langage-clair, ocr, administratif, belgique]"
date_added: "2026-03-31"
---

# Lexavo Decode — Traducteur de Documents Juridiques

Transforme n'importe quel document administratif ou juridique belge en explication
claire, points d'action et délais à respecter.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/decode/analyze` | Analyse texte brut |
| POST | `/decode/upload` | Upload PDF ou image (OCR automatique) |

## Structure de la réponse

```json
{
  "plain_summary": "Ce document est une mise en demeure de payer 500€...",
  "document_type": "mise_en_demeure",
  "key_points": [
    "Vous devez payer 500€",
    "Délai imposé : 15 jours calendriers"
  ],
  "action_required": "Payer ou contester dans les 15 jours",
  "deadline": "2026-04-15",
  "urgency": "high",
  "legal_context": "Art. 1341 Code civil belge — mise en demeure formelle",
  "disclaimer": "Traduction informelle. Consultez un professionnel pour actes officiels."
}
```

## Types de documents traités

| Type de document | Branche du droit invoquée |
|-----------------|--------------------------|
| Mise en demeure | `droit-civil` |
| Décision SPF Finances | `droit-fiscal` |
| Convocation tribunal | `droit-penal` ou `droit-civil` |
| Avis d'imposition | `droit-fiscal` |
| Lettre ONEM | `droit-securite-sociale` |
| Décision IBGE / OVAM | `droit-environnement` |
| Jugement en néerlandais | Traduction NL→FR + branche applicable |
| Acte notarial | `droit-civil` + `droit-immobilier` |

## Pipeline OCR

```python
# PDF avec texte natif → extraction directe PyMuPDF
# PDF scanné → PyMuPDF + fallback pytesseract lang="fra+nld"
# Image JPG/PNG/TIFF → pytesseract lang="fra+nld+eng"
# Min 20 caractères extraits requis
```

## Modèle Claude utilisé

`claude-haiku-4-5` via model_router — tâche de traduction/simplification.
~80% moins cher que Sonnet pour cette tâche répétitive.

## Niveaux d'urgence

| Urgence | Signaux | Délai type |
|---------|---------|-----------|
| `critical` | "immédiatement", "sous peine de..." | < 48h |
| `high` | "dans les 15 jours", "sous huitaine" | 7-15 jours |
| `medium` | "dans le mois", "avant le..." | 30 jours |
| `low` | Informatif, aucun délai | Pas de délai |

## Skills juridiques intégrés

- `droit-administratif` → décisions administratives, recours Conseil d'État
- `droit-fiscal` → avis d'imposition, contrôles SPF, délais de réclamation
- `droit-securite-sociale` → lettres ONEM, INAMI, décisions prestations
- `humanizer` → OBLIGATOIRE sur toute réponse Decode (accessibilité maximale)
- `enterprise-search:knowledge-synthesis` → enrichir avec contexte juridique

## Gestion du néerlandais (Flandre)

1. OCR avec `lang="nld"` ou `lang="fra+nld"`
2. Traduction NL→FR via Claude
3. Analyse juridique en FR
4. Réponse dans la langue de l'utilisateur (FR/NL selon `language` param)
