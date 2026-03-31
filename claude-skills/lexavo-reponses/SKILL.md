---
name: lexavo-reponses
description: >
  Générer une réponse à un courrier juridique reçu (mise en demeure, licenciement,
  avis d'expulsion, convocation, décision administrative). Déclencher quand l'utilisateur
  reçoit un document juridique et veut savoir comment répondre.
category: lexavo
risk: safe
tags: "[reponses, courriers, droit-belge, mise-en-demeure, licenciement]"
date_added: "2026-03-31"
---

# Lexavo Réponses — Générateur de Réponses Juridiques

Analyse un courrier juridique reçu et génère une réponse adaptée avec références légales.

## Endpoint API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/response/generate` | Génère une réponse au courrier |

## Paramètres

```json
{
  "received_text": "Texte du courrier reçu...",
  "user_context": "Je suis locataire depuis 5 ans..." (optionnel)
}
```

## Structure de la réponse

```json
{
  "response_letter": "Madame, Monsieur...",
  "legal_references": [
    {"article": "Art. 97 Code du Logement", "summary": "..."}
  ],
  "next_steps": ["Envoyer en recommandé", "Conserver une copie"],
  "urgency_level": "high",
  "deadline": "15 jours",
  "disclaimer": "..."
}
```

## Types de courriers traités

| Type | Branche invoquée |
|------|-----------------|
| Mise en demeure | `droit-civil` |
| Licenciement | `droit-travail` |
| Avis d'expulsion | `droit-immobilier` |
| Décision administrative | `droit-administratif` |
| Convocation ONSS/SPF | `droit-securite-sociale` |
| Décision APD (RGPD) | `droit-fondamentaux` |

## Skills juridiques intégrés

- `droit-civil` → obligations, délais, intérêts de retard
- `droit-travail` → lettres de licenciement, recours au tribunal du travail
- `droit-immobilier` → réponses aux bailleurs, garantie locative
- `droit-administratif` → recours Conseil d'État, délais
- `humanizer` → appliquer sur la lettre finale pour ton naturel

## Modèle Claude utilisé

`claude-sonnet-4-6` via model_router — tâche d'analyse + rédaction.

## Prompt engineering

Prompt système optimisé avec :
- Détection automatique du type de courrier
- Extraction des délais légaux applicables
- Génération de lettre formelle belge (formules de politesse standard)
- Références articles de loi systématiques
