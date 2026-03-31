---
name: lexavo-compliance
description: >
  Audit de conformité B2B belge en 15 questions. Déclencher pour : audit RGPD,
  conformité commerciale, vérification obligations légales PME, rapport de compliance,
  préparation à une inspection. Pour indépendants, SPRL, SRL, ASBL.
category: lexavo
risk: safe
tags: "[compliance, rgpd, b2b, audit, belgique, pme]"
date_added: "2026-03-31"
---

# Lexavo Compliance — Audit B2B Belge

15 questions couvrant 6 domaines de conformité pour PME et indépendants belges.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/compliance/questions` | Retourne les 15 questions |
| POST | `/compliance/audit` | Génère le rapport d'audit |

## Les 6 Domaines (15 questions)

| Domaine | Questions | Législation |
|---------|-----------|-------------|
| RGPD | 3 | RGPD UE 2016/679, Loi 30/07/2018 |
| Commercial | 2 | Code des sociétés et associations (CSA) |
| Travail | 3 | Loi du 5/12/1968, CCT nationales |
| Social | 3 | Loi ONSS, arrêtés royaux |
| Assurance | 2 | Loi Landthorst 25/06/1992 |
| Fiscal | 2 | CIR 1992, Code TVA |

## Structure du rapport

```json
{
  "compliance_score": 67,
  "risk_level": "medium",
  "compliant_items": [...],
  "non_compliant_items": [
    {
      "question": "Registre des traitements de données ?",
      "category": "rgpd",
      "risk": "high",
      "risk_description": "Amende APD jusqu'à 4% du CA mondial",
      "action_required": "Créer le registre des traitements (Art. 30 RGPD)",
      "legal_basis": "Art. 30 RGPD"
    }
  ],
  "priority_actions": [...],
  "disclaimer": "Audit indicatif. Ne remplace pas un audit professionnel certifié."
}
```

## Types d'entreprise

| Type | Particularités |
|------|----------------|
| `independant` | Pas d'obligations ONSS employeur, CGV simplifiées |
| `srl` | CSA complet, registre UBO, assemblée générale annuelle |
| `asbl` | Loi ASBL 27/06/1921, obligations comptables spécifiques |

## Niveaux de risque

| Score | Niveau | Action |
|-------|--------|--------|
| 80-100 | `low` | Maintenir le niveau, veille législative |
| 60-79 | `medium` | Actions correctives sous 3 mois |
| 40-59 | `high` | Actions correctives urgentes |
| < 40 | `critical` | Consultation juridique immédiate |

## Skills juridiques intégrés

- `droit-fondamentaux` → RGPD, APD, Charte UE droits fondamentaux
- `droit-commercial` → CSA, obligations SRL/ASBL, registre UBO
- `droit-travail` → obligations employeur, règlement de travail, ONSS
- `droit-fiscal` → TVA, CIR, obligations déclaratives mensuelles/annuelles
- `droit-securite-sociale` → cotisations sociales, INAMI, assurances

## Intégration Promptflow

```python
# Flow d'audit interactif avec questions conditionnelles
# Questions adaptées selon le type d'entreprise (independant/srl/asbl)
# Rapport PDF généré automatiquement via WeasyPrint + branding Lexavo
```
