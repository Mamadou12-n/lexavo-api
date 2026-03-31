---
name: lexavo-shield
description: >
  Analyser un contrat en droit belge avec verdict feu tricolore (vert/orange/rouge).
  Déclencher pour : analyser un contrat, vérifier des clauses, uploader un PDF de contrat,
  voir l'historique des analyses, détecter des clauses abusives, obtenir des sources légales.
category: lexavo
risk: safe
tags: "[contrats, droit-belge, ocr, rag, analyse-juridique]"
date_added: "2026-03-31"
---

# Lexavo Shield — Analyse de Contrats

Analyse un contrat et retourne un verdict feu tricolore avec explication clause par clause.
Intègre OCR pour PDF/images + RAG sur les sources juridiques belges.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/shield/analyze` | Analyse texte brut |
| POST | `/shield/upload` | Upload PDF ou image (OCR automatique) |
| GET | `/shield/history` | Historique des analyses |

## Structure de la réponse

```json
{
  "verdict": "orange",
  "summary": "Contrat de bail avec 2 clauses problématiques",
  "clauses": [
    {
      "clause_text": "Le bailleur peut résilier sans préavis",
      "status": "red",
      "explanation": "Contraire à l'art. 97 §3 du Code du Logement",
      "legal_basis": "Art. 97 §3 Code du Logement bruxellois"
    }
  ],
  "contract_type_detected": "bail",
  "legal_sources": [...],
  "disclaimer": "Outil d'information juridique. Ne remplace pas un avis professionnel."
}
```

## Verdicts

| Couleur | Signification |
|---------|---------------|
| 🟢 `green` | Contrat standard, aucune clause problématique détectée |
| 🟡 `orange` | Clauses inhabituelles ou potentiellement désavantageuses |
| 🔴 `red` | Clauses illégales ou très risquées selon le droit belge |

## Types de contrats détectés automatiquement

- `bail` — Contrat de bail (résidentiel, Bruxelles/Wallonie/Flandre)
- `travail` — Contrat de travail CDI/CDD
- `vente` — Contrat de vente entre particuliers
- `general` — Tout autre type de contrat

## Skills juridiques intégrés

Invoke ces skills selon le type détecté :
- `droit-immobilier` → si type = bail
- `droit-travail` → si type = travail
- `droit-civil` → si type = vente ou général
- `droit-fondamentaux` → vérification RGPD dans les clauses de données

## Intégration NotebookLM (sources longues)

Pour les contrats > 10 000 caractères, utiliser `notebooklm` pour créer un notebook d'analyse :
```python
# Créer un notebook NotebookLM avec le contrat comme source
# Poser des questions : "Quelles clauses sont contraires au droit belge ?"
# Utiliser le digest pour enrichir l'analyse RAG
```

## Paramètres

| Paramètre | Type | Description |
|-----------|------|-------------|
| `contract_text` | string (min 50) | Texte du contrat |
| `contract_type` | string (optionnel) | Force le type : bail, travail, vente |

## Modèle Claude utilisé

- Contrats < 5000 chars → `claude-sonnet-4-6` (via model_router)
- Contrats > 15000 chars → `claude-opus-4-6`

## Règle légale absolue

Toujours inclure le disclaimer :
> "Outil d'information juridique. Ne remplace pas un avis professionnel d'avocat."
