---
name: lexavo-audit
description: >
  Audit de conformite juridique pour PME et entreprises belges.
  30 questions, 8 domaines du droit, score sur 100, recommandations IA.
  Declencheur : audit, conformite entreprise, verification legale PME.
category: lexavo
risk: safe
tags: "[audit, conformite, pme, entreprise, belgique, rgpd, travail, fiscal]"
date_added: "2026-04-01"
---

# Lexavo Audit Entreprise — Conformite juridique belge

Audit complet de conformite pour PME et entreprises belges.
30 questions couvrant 8 domaines du droit : RGPD, travail, fiscal,
commercial, societes, environnement, gouvernance, PI.

## Endpoints API

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/audit/questions?company_type=srl` | Questions d'audit adaptees au type |
| POST | `/audit/generate` | Generer le rapport d'audit complet |
| GET | `/audit/history` | Historique des audits (auth requise) |

## Parametres /audit/generate

```json
{
  "answers": [
    {"question_id": 1, "answer": "yes"},
    {"question_id": 2, "answer": "no"},
    {"question_id": 3, "answer": "partial"}
  ],
  "company_type": "srl",
  "company_name": "Ma Societe SRL",
  "sector": "IT",
  "employees": 15
}
```

Reponses possibles : `yes` (conforme), `no` (non conforme), `partial` (partiellement), `na` (non applicable)

## Reponse

```json
{
  "score": 72,
  "verdict": "orange",
  "verdict_label": "Conformite partielle — actions requises",
  "critical_risks": [...],
  "category_results": {
    "rgpd": {"score": 85, "verdict": "green"},
    "travail": {"score": 50, "verdict": "orange"},
    "fiscal": {"score": 100, "verdict": "green"}
  },
  "recommendations": [
    {
      "priority": "high",
      "action": "Deposer le reglement de travail au SPF Emploi",
      "deadline": "30 jours",
      "legal_ref": "Loi du 8/4/1965"
    }
  ]
}
```

## Types d'entreprise supportes

| ID | Label |
|----|-------|
| srl | SRL (Societe a responsabilite limitee) |
| sa | SA (Societe anonyme) |
| sc | SC (Societe cooperative) |
| independant | Independant / Personne physique |
| asbl | ASBL |
| pme | PME (< 50 employes) |
| grande_entreprise | Grande entreprise (50+ employes) |

## 8 domaines audites

1. **RGPD & Vie privee** (5 questions) — registre, DPIA, DPO, DPA, politique
2. **Droit du travail** (5 questions) — contrats, reglement, CPPT, elections
3. **Droit fiscal** (4 questions) — TVA, factures, ISOC, prix transfert
4. **Droit commercial** (4 questions) — CGV, BCE, delais paiement, blanchiment
5. **Droit des societes** (4 questions) — CSA, comptes annuels, UBO, liquidite
6. **Environnement** (3 questions) — permis, dechets, PEB
7. **Gouvernance** (3 questions) — code conduite, lanceurs d'alerte, RC mandataires
8. **Propriete intellectuelle** (2 questions) — marques, cession PI

## Restriction d'acces

Reserve aux plans **Business** (79,99€/mois), **Firm** et **Enterprise**.
Pendant la beta : accessible a tous gratuitement.

## Skills invoquees

- `droit-travail` → questions 6-10
- `droit-fiscal` → questions 11-14
- `droit-commercial` → questions 15-18
- `droit-environnement` → questions 23-25
- `droit-propriete-intellectuelle` → questions 29-30

## Mise a jour automatique

Les questions d'audit sont mises a jour automatiquement via GitHub Actions
chaque lundi pour refleter les evolutions legislatives belges.
