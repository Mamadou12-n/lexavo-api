---
name: lexavo-litiges
description: >
  Recouvrement d'impayés automatisé en 4 étapes. Déclencher pour :
  facture impayée, client qui ne paye pas, relancer un débiteur,
  générer une mise en demeure, initier une procédure IOS (injonction de payer).
  Pour indépendants, PME et particuliers belges.
category: lexavo
risk: safe
tags: "[litiges, recouvrement, impayes, mise-en-demeure, ios, belgique]"
date_added: "2026-03-31"
---

# Lexavo Litiges Pro — Recouvrement d'Impayés

Séquence automatisée de recouvrement : rappel amiable → rappel ferme → mise en demeure → IOS.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/litigation/stages` | Liste les 4 étapes de la procédure |
| POST | `/litigation/start` | Démarre la procédure de recouvrement |

## Les 4 Étapes

| Étape | Nom | J+ | Description |
|-------|-----|-----|-------------|
| 1 | Rappel amiable | 15 | Rappel courtois par email/courrier |
| 2 | Rappel ferme | 30 | Mention des intérêts de retard légaux |
| 3 | Mise en demeure | 45 | Recommandé formel avec AR |
| 4 | Recouvrement | 60 | Procédure IOS ou mise en relation avocat |

## Paramètres de démarrage

```json
{
  "creditor_name": "Mon Entreprise SPRL",
  "debtor_name": "Client Défaillant SA",
  "amount": 5000.00,
  "invoice_number": "FAC-2026-001",
  "due_date": "2026-02-15"
}
```

## Réponse

```json
{
  "litigation_id": "LIT-20260331-0001",
  "current_stage": "rappel_amiable",
  "stages": [
    {"stage": 1, "name": "rappel_amiable", "scheduled_date": "2026-04-15", "status": "active"},
    {"stage": 2, "name": "rappel_ferme", "scheduled_date": "2026-04-30", "status": "pending"},
    ...
  ],
  "current_letter": "Madame, Monsieur,\n\nSauf erreur...",
  "legal_basis": "Loi du 2 août 2002 (retard de paiement)",
  "disclaimer": "Modèles de lettres types. Ne constituent pas un acte d'huissier."
}
```

## Base légale belge

| Règle | Source |
|-------|--------|
| Intérêts de retard B2B | Loi du 2 août 2002 (transactions commerciales) |
| Taux intérêt 2026 | BCE + 8% (taux officiel BCE + marge légale) |
| Clause pénale | Art. 1226 Code civil belge |
| Procédure IOS | Art. 1338 à 1380 Code judiciaire |
| Prescription créance | Art. 2262bis Code civil (10 ans civil, 5 ans commercial) |

## Skills juridiques intégrés

- `droit-commercial` → créances commerciales, intérêts de retard B2B, prescription
- `droit-civil` → créances civiles, clause pénale, saisie conservatoire
- `lexavo-contrats` → générer la mise en demeure en PDF (WeasyPrint)

## Limites légales importantes

⚠️ Les lettres générées sont des **modèles types informatifs**.
Pour la procédure IOS (injonction de payer, Art. 1338bis Cj.), l'intervention d'un
avocat ou d'un huissier est requise. Utiliser `lexavo-match` pour mise en relation.

## Intégration lexavo-contrats

```python
# Générer la mise en demeure en PDF avec branding Lexavo
result = generate_contract_html(
    template_id="mise_en_demeure",
    variables={
        "creancier": creditor_name,
        "debiteur": debtor_name,
        "montant": amount,
        "facture": invoice_number,
        "date_echeance": due_date
    }
)
pdf = generate_pdf(result["html"], title=f"Mise en demeure — {invoice_number}")
```
