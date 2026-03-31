---
name: lexavo-proof
description: >
  Construire son dossier juridique avec timestamps automatiques. Déclencher pour :
  documenter des faits au fil du temps, constituer des preuves, préparer un dossier
  pour un avocat, journaliser harcèlement/voisinage/litige. Types : faits, preuves,
  témoins, documents.
category: lexavo
risk: safe
tags: "[proof, dossier, preuves, timestamps, documentation, belgique]"
date_added: "2026-03-31"
---

# Lexavo Proof — Constructeur de Dossier

Outil de journalisation juridique avec timestamps automatiques pour constituer
un dossier solide au fil du temps.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/proof/create` | Crée un nouveau dossier |
| POST | `/proof/{id}/add-entry` | Ajoute une entrée |

## Création d'un dossier

```json
{
  "title": "Harcèlement au travail — Employeur X",
  "category": "travail",
  "description": "Documentation des actes de harcèlement depuis janvier 2026"
}
```

## Types d'entrées

| Type | Description | Exemple |
|------|-------------|---------|
| `fait` | Fait observé avec date/heure | "Employeur a crié devant témoins" |
| `preuve` | Élément de preuve documenté | "Email reçu le 15/03/2026 à 9h12" |
| `temoin` | Témoin potentiel | "Mme Dupont présente lors de l'incident" |
| `document` | Référence à un document | "Contrat de travail signé le 01/01/2025" |

## Structure d'une entrée

```json
{
  "entry_id": 3,
  "type": "fait",
  "content": "Employeur a refusé la demande de congé sans justification",
  "evidence_description": "Message WhatsApp conservé",
  "timestamp": "2026-03-31T14:23:00",
  "verified": false
}
```

## Résumé du dossier

```json
{
  "case_id": "PROOF-20260331-001",
  "total_entries": 12,
  "types_count": {"fait": 7, "preuve": 3, "temoin": 2},
  "date_range": {"first": "2026-01-15", "last": "2026-03-31"},
  "status": "open"
}
```

## Catégories de dossiers

- `travail` → harcèlement, discrimination, licenciement abusif
- `voisinage` → nuisances, dégradations, violences
- `bail` → dégâts locatifs, refus réparations
- `famille` → non-respect décisions judiciaires
- `commercial` → litige contractuel, fraude
- `general` → tout autre litige

## Intégration NotebookLM

Pour les dossiers complexes (> 20 entrées) :
```python
# Créer un notebook NotebookLM avec toutes les entrées comme sources
# Poser des questions : "Quelle est la chronologie des faits ?"
# Générer un résumé structuré pour l'avocat
# Exporter en PDF professionnel (WeasyPrint)
```

## Skills juridiques intégrés

- `droit-travail` → harcèlement au travail (Loi du 4/08/1996)
- `droit-civil` → preuves civiles (Art. 8.1 NCPC)
- `droit-penal` → éléments constitutifs d'une infraction

## Valeur probante

⚠️ Le journal Lexavo Proof est un outil de documentation personnelle.
La valeur probante devant un tribunal dépend de l'appréciation du juge.
Consultez un avocat pour la constitution formelle d'un dossier juridique.
