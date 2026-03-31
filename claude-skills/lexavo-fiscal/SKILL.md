---
name: lexavo-fiscal
description: >
  Copilote fiscal belge pour indépendants et PME. Déclencher pour : questions TVA,
  déductions fiscales, CIR 1992, ISOC, déclarations IPP, frais professionnels,
  cotisations sociales, planning fiscal, obligations déclaratives. Cite toujours
  l'article applicable (CIR, CTVA, AR, circulaire administrative).
category: lexavo
risk: safe
tags: "[fiscal, tva, ipp, isoc, cir1992, independants, belgique]"
date_added: "2026-03-31"
---

# Lexavo Fiscal — Copilote TVA et Impôts Belges

Assistant fiscal pour indépendants et PME belges. Répond aux questions fiscales
quotidiennes avec références légales précises (CIR 1992, Code TVA, doctrine).

## Endpoint API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/fiscal/ask` | Pose une question fiscale |

## Paramètre

```json
{
  "question": "Est-ce que mes frais de restaurant avec des clients sont déductibles ?"
}
```

## Structure de la réponse

```json
{
  "answer": "Les frais de restaurant professionnels sont déductibles à 69%...",
  "legal_references": [
    {
      "article": "Art. 53, 8° CIR 1992",
      "summary": "Déductibilité limitée à 69% pour frais de réception et restaurant"
    }
  ],
  "deadlines": [],
  "applies_to": ["independant", "societe"],
  "warning": "Le fisc peut requalifier si caractère privé predominant",
  "disclaimer": "Information fiscale générale. Consultez votre comptable."
}
```

## Domaines couverts (RAG droit_fiscal)

| Domaine | Sources RAG |
|---------|------------|
| IPP | CIR 1992, circulaires SPF Finances |
| ISOC | CIR 1992, commentaire administratif |
| TVA | Code TVA, BTWO, circulaires TVA |
| Droits d'enregistrement | Code des droits d'enregistrement |
| Succession | Codes régionaux (Bruxelles/Wallonie/VLABEL) |
| ONSS | Arrêtés royaux ONSS |

## Questions types traitées

- Frais professionnels déductibles (voiture, téléphone, bureau à domicile)
- Régimes TVA (franchise, régime normal, co-contractant)
- Cotisations sociales indépendant (calcul, délais)
- Avantages de toute nature (ATN voiture, gsm, pc)
- Planning salarial vs dividendes
- Déduction intérêts notionnels (si encore applicable)

## Modèle Claude utilisé

`claude-sonnet-4-6` via model_router — analyse + références légales.

## Intégration NotebookLM

Pour les questions fiscales complexes nécessitant des sources étendues :
```python
# Créer notebook avec : circulaires SPF Finances, commentaire CIR
# Poser la question fiscale complexe
# Obtenir une réponse avec citations précises
# Particulièrement utile pour : ruling fiscal, contrôle fiscal, planification
```

## Skills juridiques intégrés

- `droit-fiscal` → sources RAG fiscales belges, doctrine administrative
- `droit-commercial` → obligations déclaratives entreprises
- `droit-securite-sociale` → cotisations ONSS / INASTI

## Disclaimer fiscal obligatoire

Toujours inclure :
> "Information fiscale générale. Ne constitue pas un conseil fiscal personnalisé.
> Consultez votre comptable ou un conseiller fiscal agréé (IEC/IPCF)."

## Règle ZÉRO INVENTION

Ne JAMAIS inventer des taux, des articles ou des délais.
Si la réponse n'est pas dans le RAG → "Je ne dispose pas de sources suffisantes
pour cette question. Consultez le commentaire CIR sur fisconet.be."
