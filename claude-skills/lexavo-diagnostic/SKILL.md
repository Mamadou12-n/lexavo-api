---
name: lexavo-diagnostic
description: >
  Diagnostic juridique personnalisé en 6 questions. Déclencher quand l'utilisateur
  veut évaluer sa situation juridique, ne sait pas quelle branche du droit s'applique,
  veut un plan d'action juridique personnalisé, ou commence son parcours Lexavo.
category: lexavo
risk: safe
tags: "[diagnostic, questionnaire, branches-droit, plan-action, belgique]"
date_added: "2026-03-31"
---

# Lexavo Diagnostic — Orientation Juridique en 6 Questions

Questionnaire de 6 questions pour identifier la branche du droit applicable
et générer un rapport d'orientation avec plan d'action personnalisé.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/diagnostic/questions` | Retourne les 6 questions |
| POST | `/diagnostic/analyze` | Génère le diagnostic avec les réponses |

## Les 6 Questions

| # | Domaine | Question |
|---|---------|----------|
| 1 | Situation | Quelle est votre situation ? |
| 2 | Problème | Quel problème rencontrez-vous ? |
| 3 | Partie adverse | Qui est la partie adverse ? |
| 4 | Urgence | Y a-t-il une urgence ? (procédure, délai) |
| 5 | Région | Dans quelle région êtes-vous ? |
| 6 | Résolution | Comment souhaitez-vous résoudre ? |

## Branches détectables

- Travail (employeur, licenciement, harcèlement)
- Immobilier (bail, propriété, voisinage)
- Famille (divorce, garde, pension)
- Civil (contrat, dette, responsabilité)
- Pénal (infraction, victime)
- Administratif (administration, refus, fonction publique)
- Commercial (entreprise, faillite, RGPD)
- Fiscal (impôts, TVA, amendes)
- Sécurité sociale (chômage, maladie, pension)
- Étrangers (séjour, asile)

## Structure du rapport diagnostic

```json
{
  "title": "Diagnostic : Litige de bail résidentiel",
  "detected_branch": "droit_immobilier",
  "applicable_rights": ["Droit à la garantie locative", "Droit au préavis légal"],
  "risks": ["Expulsion si délai non respecté", "Perte de la garantie"],
  "priority_actions": ["Consulter un avocat immobilier", "Envoyer recommandé"],
  "recommended_features": ["lexavo-shield", "lexavo-reponses", "lexavo-match"],
  "disclaimer": "..."
}
```

## Intégration Promptflow (Microsoft)

Pour les questionnaires conversationnels complexes :
```python
# Utiliser promptflow pour chaîner les 6 questions
# Adapter la question suivante selon la réponse précédente
# Branching logic : réponse "pénal" → questions spécifiques pénales
```

## Skills juridiques invoqués dynamiquement

Selon la branche détectée, invoquer le skill correspondant :
- `droit-travail`, `droit-immobilier`, `droit-familial`, etc.
- Toujours invoquer `humanizer` sur le rapport final
