---
name: droit-fiscal
version: 1.0.0
description: |
  Skill specialise en droit fiscal belge. Couvre l'IPP, l'ISOC, la TVA, les droits
  d'enregistrement, les droits de succession, le precompte mobilier, la procedure fiscale.
  Sources : SPF Finances, Moniteur belge, Juridat, Conseil d'Etat.
triggers:
  - "droit fiscal"
  - "impots"
  - "TVA"
  - "IPP"
  - "ISOC"
  - "precompte"
  - "droits de succession"
  - "droits d'enregistrement"
  - "SPF Finances"
  - "declaration fiscale"
  - "taxe"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit fiscal belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["SPF Finances", "Moniteur belge", "Juridat", "Conseil d'État", "Cour constitutionnelle"]
KEYWORDS = [
    "impot des personnes physiques", "IPP", "ISOC", "TVA",
    "precompte mobilier", "precompte immobilier", "precompte professionnel",
    "droits d'enregistrement", "droits de succession", "procedure fiscale",
    "ruling fiscal", "abus fiscal", "deduction", "reduction d'impot",
    "regime fiscal", "contribution complementaire", "taxe communale",
    "convention preventive double imposition", "prix de transfert"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Code des impots sur les revenus 1992 (CIR 92) | Loi du 10 avril 1992 |
| Code de la TVA | Code du 3 juillet 1969 |
| Code des droits d'enregistrement | Code du 30 novembre 1939 |
| Code des droits de succession | Code du 31 mars 1936 |
| Loi generale relative aux douanes et accises | Loi du 18 juillet 1977 |
| Code du recouvrement amiable et force | Loi du 13 avril 2019 |
| AR/CIR 92 | Arrete d'execution du CIR 92 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — SPF Finances pour les circulaires, Juridat pour la jurisprudence
2. `top_k=8` — la matiere fiscale est technique et dense
3. Attention aux differences regionales : droits d'enregistrement et succession regionalises depuis 2001
4. Distinguer clairement federal (IPP, ISOC, TVA) vs regional (droits d'enregistrement, succession, precompte immobilier)
5. Les rulings du SDA sont dans la source SPF Finances

## Regles d'or

1. **Zero invention** : ne jamais inventer de taux d'imposition, de montants exoneres ou de baremes. Les chiffres fiscaux changent chaque annee — toujours preciser l'exercice d'imposition.
2. **Double verification** : les montants indexes changent annuellement. Toujours verifier la date de la source.
3. **Zero hallucination** : la fiscalite est une matiere ou les erreurs coutent cher. Toujours recommander un conseil fiscal.
4. **Humanizer** : simplifier le jargon fiscal pour les particuliers. Garder la precision technique pour les professionnels.
5. **Mise a jour** : les lois de finances modifient le CIR 92 chaque annee. Les sources datant de plus de 2 ans doivent etre signalees.
