---
name: droit-commercial
version: 1.0.0
description: |
  Skill specialise en droit commercial et des societes belge. Couvre le CSA, les pratiques
  du marche, l'insolvabilite, le droit de la concurrence, le droit bancaire et financier.
  Sources : Moniteur belge, Juridat, FSMA, EUR-Lex.
triggers:
  - "droit commercial"
  - "droit des societes"
  - "CSA"
  - "societe"
  - "faillite"
  - "insolvabilite"
  - "concurrence"
  - "FSMA"
  - "pratiques du marche"
  - "entreprise"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit commercial et des societes belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Moniteur belge", "Juridat", "FSMA", "EUR-Lex", "Cour constitutionnelle"]
KEYWORDS = [
    "Code des societes et des associations", "CSA", "SRL", "SA", "SC",
    "faillite", "reorganisation judiciaire", "insolvabilite",
    "pratiques du marche", "concurrence", "abus de position dominante",
    "clause abusive", "garantie commerciale", "droit bancaire",
    "marches financiers", "prospectus", "transparence",
    "responsabilite des administrateurs", "action sociale", "action minoritaire",
    "droit economique", "Code de droit economique"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Code des societes et des associations (CSA) | Loi du 23 mars 2019 |
| Code de droit economique (CDE) | Loi du 28 fevrier 2013 |
| Livre XX CDE (insolvabilite) | Loi du 11 aout 2017 |
| Loi sur les pratiques du marche | Livre VI CDE |
| Loi sur la protection du consommateur | Livre VI CDE |
| Loi sur les services financiers | Loi du 2 aout 2002 |
| Loi anti-blanchiment | Loi du 18 septembre 2017 |
| Reglement FSMA | Reglements et circulaires FSMA |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — FSMA pour la reglementation financiere, Juridat pour la jurisprudence
2. `top_k=6` standard
3. Le CSA a remplace le Code des societes depuis le 1er mai 2019 — attention aux anciennes references
4. Pour les questions de droit europeen de la concurrence, inclure EUR-Lex
5. Les arrets de la cour d'appel de Bruxelles (marche reglemente) sont dans Juridat

## Regles d'or

1. **Zero invention** : ne jamais inventer de reference d'article du CSA ou du CDE. La numerotation est specifique (ex. art. 5:153 CSA).
2. **Double verification** : verifier si la disposition citee est bien du CSA (post-2019) et non de l'ancien Code des societes.
3. **Zero hallucination** : ne pas confondre formes societaires (SRL vs SPRL, SA ancien vs SA nouveau regime).
4. **Humanizer** : adapter le niveau. Entrepreneur individuel vs avocat d'affaires ont des besoins differents.
5. **Mise a jour** : le CSA evolue. Verifier les modifications recentes au Moniteur belge.
