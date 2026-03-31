---
name: droit-penal
version: 1.0.0
description: |
  Skill specialise en droit penal belge. Couvre les infractions, les peines, la procedure
  penale, les droits de la defense, la detention preventive, les mesures alternatives,
  le nouveau Code penal. Sources : Juridat, Moniteur belge, Cour constitutionnelle, HUDOC.
triggers:
  - "droit penal"
  - "infraction"
  - "delit"
  - "crime"
  - "peine"
  - "detention"
  - "casier judiciaire"
  - "plainte"
  - "parquet"
  - "instruction"
  - "tribunal correctionnel"
  - "cour d'assises"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit penal belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Juridat", "Moniteur belge", "Cour constitutionnelle", "HUDOC", "Conseil d'État"]
KEYWORDS = [
    "infraction", "peine", "detention preventive", "instruction penale",
    "parquet", "juge d'instruction", "tribunal correctionnel", "cour d'assises",
    "casier judiciaire", "mesure alternative", "probation", "surveillance electronique",
    "recidive", "prescription", "plainte", "constitution de partie civile",
    "droits de la defense", "presomption d'innocence", "mandat d'arret",
    "internement", "mediation penale"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Code penal | Loi du 8 juin 1867 |
| Nouveau Code penal (Livre 1) | Loi du 29 fevrier 2024 |
| Code d'instruction criminelle | Loi du 17 novembre 1808 |
| Loi sur la detention preventive | Loi du 20 juillet 1990 |
| Loi relative a la protection de la jeunesse | Loi du 8 avril 1965 |
| Loi sur le statut juridique externe des detenus | Loi du 17 mai 2006 |
| Loi sur les peines | Loi du 4 octobre 2019 (revision) |
| Loi Franchimont (droits de la defense) | Loi du 12 mars 1998 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — Juridat pour les arrets de cassation penale
2. `top_k=6` standard
3. Attention au nouveau Code penal Livre 1 (entree en vigueur progressive)
4. Pour les droits fondamentaux (art. 5, 6 CEDH), inclure HUDOC
5. Distinguer ancien Code penal (encore en vigueur pour le Livre 2) vs nouveau Code

## Regles d'or

1. **Zero invention** : ne jamais inventer de qualification penale, de peine ou de reference d'arret. Les erreurs en droit penal ont des consequences graves.
2. **Double verification** : chaque reference d'arret de cassation doit etre verifiee dans ChromaDB.
3. **Zero hallucination** : ne jamais affirmer qu'un fait constitue une infraction sans citer le texte legal precis.
4. **Humanizer** : ton serieux et precis. Adapter le vocabulaire au public (victime vs avocat penaliste).
5. **Mise a jour** : le nouveau Code penal entre en vigueur progressivement. Verifier quelle version s'applique.
