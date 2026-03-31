---
name: lexavo-heritage
description: >
  Guide succession personnalisé par région belge après un décès. Déclencher pour :
  décès d'un proche, questions sur les droits de succession, guide étape par étape,
  calcul des droits par région (Bruxelles/Wallonie/Flandre), impact d'un testament,
  présence de biens immobiliers dans la succession.
category: lexavo
risk: safe
tags: "[heritage, succession, deces, droits-succession, notaire, belgique]"
date_added: "2026-03-31"
---

# Lexavo Héritage — Guide Succession Belge

Guide personnalisé de succession adapté à la région, au lien de parenté
et à la situation spécifique (testament, immobilier, etc.)

## Endpoint API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/heritage/guide` | Génère le guide personnalisé |

## Paramètres

```json
{
  "region": "bruxelles",
  "relationship": "direct_line",
  "has_testament": true,
  "has_real_estate": true,
  "estimated_value": 250000
}
```

## Les 4 Étapes communes

| Étape | Titre | Délai |
|-------|-------|-------|
| 1 | Décès et formalités immédiates | 24-48h |
| 2 | Choix successoral | 3 mois |
| 3 | Déclaration de succession | 4 mois |
| 4 | Partage | Variable |

## Spécificités régionales

### Bruxelles (SPF Finances)
- Délai déclaration : 4 mois (BE), 5 mois (EU), 6 mois (hors EU)
- Abattement conjoint : 25.000€ sur logement familial
- Taux ligne directe : 3% → 8% → 27%

### Wallonie (SPF Finances)
- Délai déclaration : 4 mois
- Exemption totale conjoint sur logement familial (sous conditions)
- Taux ligne directe : 3% → 9% → 24%

### Flandre (VLABEL)
- Délai déclaration : 4 mois
- Vrijstelling gezinswoning voor partner
- Forfait mobilier : 20.000€
- Taux ligne directe : 3% → 9% → 27%

## Liens de parenté

| Relation | Taux | Exemptions |
|----------|------|-----------|
| `direct_line` | Ligne directe (enfants, parents) | Les plus favorables |
| `siblings` | Frères et sœurs | Taux intermédiaires |
| `others` | Autres | Taux les plus élevés |

## Intégration calculateurs

Appelle automatiquement `lexavo-calculateurs` pour le calcul des droits de succession
si `estimated_value > 0`.

## Intégration NotebookLM

Pour les successions complexes :
```python
# Créer notebook avec : acte de décès, testament, inventaire biens
# Poser : "Quels sont les droits de succession applicables ?"
# Générer guide PDF personnalisé pour les héritiers
```

## Skills juridiques intégrés

- `droit-civil` → droit des successions (Code civil Art. 731 et suiv.)
- `droit-fiscal` → droits de succession par région
- `droit-familial` → présence d'enfants mineurs, autorité parentale

## Disclaimer obligatoire

> "Guide informatif. Les successions necessitent l'intervention d'un notaire.
> Consultez le Bureau Sécurité Juridique de votre région."
