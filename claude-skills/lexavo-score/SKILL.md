---
name: lexavo-score
description: >
  Score de santé juridique sur 100 en 10 questions. Déclencher quand l'utilisateur
  veut évaluer la conformité juridique de son entreprise ou situation personnelle,
  obtenir un score chiffré, identifier ses points faibles juridiques.
category: lexavo
risk: safe
tags: "[score, sante-juridique, conformite, questionnaire, belgique]"
date_added: "2026-03-31"
---

# Lexavo Score — Santé Juridique sur 100

10 questions pondérées pour calculer le score de santé juridique d'une entreprise ou d'un individu.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/score/questions` | Retourne les 10 questions pondérées |
| POST | `/score/evaluate` | Calcule le score avec les réponses |

## Les 10 Questions et Poids

| # | Question | Poids |
|---|---------|-------|
| 1 | Contrats clients signés ? | 15 |
| 2 | RGPD conforme ? | 15 |
| 3 | Assurance RC Pro active ? | 10 |
| 4 | Statut légal adapté ? | 10 |
| 5 | Registre UBO à jour ? | 10 |
| 6 | Contrats fournisseurs à jour ? | 10 |
| 7 | Cotisations sociales en ordre ? | 10 |
| 8 | CGV publiées ? | 5 |
| 9 | Déclarations fiscales à jour ? | 10 |
| 10 | Procédure interne plaintes ? | 5 |

## Réponses possibles

- `oui` → poids complet
- `non` → 0 points
- `partiel` → 50% du poids
- `na` → exclu du calcul

## Structure de la réponse

```json
{
  "score": 72,
  "total_possible": 85,
  "percentage": 84.7,
  "rating": "bon",
  "weak_points": [
    {
      "question": "RGPD conforme ?",
      "recommendation": "Nommer un DPO ou vérifier la politique de confidentialité",
      "legal_basis": "RGPD Art. 37"
    }
  ],
  "strong_points": [...],
  "category_breakdown": {"contrats": 85, "fiscal": 100, "social": 60},
  "disclaimer": "Score indicatif. Ne constitue pas un audit juridique."
}
```

## Ratings

| Score | Rating | Description |
|-------|--------|-------------|
| 90-100 | `excellent` | Entreprise très bien protégée |
| 70-89 | `bon` | Quelques points à améliorer |
| 50-69 | `moyen` | Risques réels identifiés |
| < 50 | `critique` | Intervention urgente recommandée |

## Skills juridiques intégrés

- `droit-commercial` → RGPD, registre UBO, CGV
- `droit-travail` → cotisations ONSS, contrats de travail
- `droit-fondamentaux` → RGPD, protection des données personnelles
- `droit-fiscal` → déclarations fiscales, TVA, obligations

## Intégration Promptflow

Pour une session de scoring interactive avec branchement conditionnel :
```python
# Flow : 10 questions en série avec logic de saut
# Adapter les recommandations selon les réponses
# Générer un rapport PDF avec WeasyPrint
```

## Après le score

Si score < 50 → recommander `lexavo-emergency` ou `lexavo-match`
Si score 50-70 → recommander `lexavo-compliance` + `lexavo-contrats`
Si score > 70 → recommander `lexavo-alertes` pour maintenir le niveau
