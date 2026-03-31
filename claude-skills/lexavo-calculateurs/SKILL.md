---
name: lexavo-calculateurs
description: >
  Calculateurs juridiques belges purs (zéro appel API). Déclencher pour :
  calculer un préavis de licenciement, une pension alimentaire, des droits de succession,
  toute question de calcul juridique belge chiffré.
category: lexavo
risk: safe
tags: "[calculateurs, droit-belge, previs, succession, pension-alimentaire, cct109]"
date_added: "2026-03-31"
---

# Lexavo Calculateurs — Calculs Juridiques Belges

Trois calculateurs purs en mathématiques belges. Zéro appel Claude — résultat instantané.

## Endpoints API

| Méthode | Endpoint | Paramètres |
|---------|----------|------------|
| POST | `/calculators/notice-period` | `years`, `monthly_salary` |
| POST | `/calculators/alimony` | `income_high`, `income_low`, `children` |
| POST | `/calculators/succession` | `region`, `amount`, `relationship` |

## 1. Calculateur Préavis (CCT n°109)

**Règle** : Art. 37/2 Loi du 26 décembre 2013

```
Formule :
- Ancienneté < 3 mois : 1 semaine
- Ancienneté 3 mois–6 mois : 3 semaines
- Ancienneté 6 mois–1 an : 4 semaines
- Ancienneté 1–2 ans : 6 semaines
- Ancienneté 2–3 ans : 7 semaines
- Chaque année supplémentaire : +3 semaines (max CCT applicable)
```

**Réponse** :
```json
{
  "weeks": 12,
  "days": 84,
  "monthly_salary": 3000.0,
  "indemnity": 9000.0,
  "legal_basis": "CCT n°109, art. 37/2 Loi 26/12/2013",
  "calculation_details": {...}
}
```

## 2. Calculateur Pension Alimentaire (Barème Renard)

**Règle** : Art. 301 §3 Code civil belge — Barème Renard

```
Base = revenu_le_plus_élevé - revenu_le_plus_bas
Pourcentage selon nombre d'enfants : 1=29%, 2=35%, 3=40%, 4+=44%
Cap à 1/3 du revenu net du débiteur
```

**Invoque** : `droit-familial` pour contexte sur la procédure de fixation

## 3. Calculateur Droits de Succession

Taux progressifs par région belge :

| Région | Autorité | Tranche 0-50K | 50-250K | 250K+ |
|--------|----------|---------------|---------|-------|
| Bruxelles | SPF Finances | 3% | 8% | 27% |
| Wallonie | SPF Finances | 3% | 9% | 24% |
| Flandre | VLABEL | 3% | 9% | 27% |

**Invoque** : `droit-fiscal` pour les exemptions régionales

## Skills juridiques intégrés

- `droit-travail` → contexte préavis, procédure licenciement
- `droit-familial` → contexte pension alimentaire, divorce
- `droit-fiscal` → droits de succession, exonérations régionales

## Règle ZÉRO INVENTION

Ces calculateurs ne font que des mathématiques. Les taux sont issus de :
- CCT n°109 (préavis)
- Art. 301 §3 Code civil (pension)
- Législation fiscale régionale en vigueur 2026

Ne jamais inventer des taux ou barèmes. Si inconnu → citer la source officielle.
