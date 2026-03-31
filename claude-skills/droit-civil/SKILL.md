---
name: droit-civil
version: 1.0.0
description: |
  Skill specialise en droit civil belge. Couvre les obligations, les contrats, la responsabilite,
  les biens, les suretes, les successions, les donations. Sources : Juridat, Moniteur belge.
  Base sur le nouveau Code civil (Livres 1 a 8).
triggers:
  - "droit civil"
  - "contrat"
  - "responsabilite civile"
  - "obligation"
  - "dommage"
  - "succession"
  - "donation"
  - "propriete"
  - "servitude"
  - "prescription"
  - "Code civil"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit civil belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Juridat", "Moniteur belge", "Cour constitutionnelle"]
KEYWORDS = [
    "contrat", "obligation", "responsabilite civile", "dommage",
    "vice de consentement", "nullite", "resolution", "resiliation",
    "force majeure", "imprevision", "garantie", "surete",
    "succession", "donation", "testament", "reserve hereditaire",
    "prescription", "propriete", "copropriete", "servitude",
    "enrichissement sans cause", "gestion d'affaires", "paiement indu"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Nouveau Code civil — Livre 1 (dispositions generales) | Loi du 13 avril 2019 |
| Nouveau Code civil — Livre 3 (biens) | Loi du 4 fevrier 2020 |
| Nouveau Code civil — Livre 4 (successions, donations, testaments) | Loi du 31 juillet 2017 |
| Nouveau Code civil — Livre 5 (obligations) | Loi du 28 avril 2022 |
| Nouveau Code civil — Livre 8 (preuve) | Loi du 13 avril 2019 |
| Ancien Code civil (dispositions encore en vigueur) | 1804 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — Juridat pour la jurisprudence de cassation
2. `top_k=6` standard
3. Attention aux reformes recentes : Livre 5 (obligations) en vigueur depuis 2023, Livre 3 (biens) depuis 2021
4. Distinguer clairement ancien Code civil vs nouveau Code civil
5. Pour les questions de responsabilite extracontractuelle : ancien regime (art. 1382-1386bis ancien CC) encore en vigueur jusqu'a adoption Livre 6

## Regles d'or

1. **Zero invention** : ne jamais inventer de reference d'article du Code civil. Le nouveau CC a une numerotation differente de l'ancien.
2. **Double verification** : verifier si la disposition citee fait partie de l'ancien ou du nouveau Code civil.
3. **Zero hallucination** : le droit civil belge est en pleine reforme. Ne pas affirmer qu'un article est en vigueur sans verifier.
4. **Humanizer** : adapter le niveau technique. Le droit civil concerne tout le monde — rester accessible.
5. **Mise a jour** : les Livres 6 (responsabilite extracontractuelle) et 7 (contrats speciaux) ne sont pas encore adoptes. Le signaler.
