---
name: droit-securite-sociale
version: 1.0.0
description: |
  Skill specialise en droit de la securite sociale belge. Couvre les allocations de chomage,
  l'assurance maladie-invalidite (INAMI), les pensions, les allocations familiales,
  les accidents du travail, les maladies professionnelles. Sources : Moniteur belge, CCE, Juridat.
triggers:
  - "securite sociale"
  - "chomage"
  - "INAMI"
  - "pension"
  - "allocations familiales"
  - "accident du travail"
  - "maladie professionnelle"
  - "mutuelle"
  - "ONEM"
  - "ONSS"
  - "incapacite de travail"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit de la securite sociale belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Moniteur belge", "CCE", "Juridat", "Cour constitutionnelle", "Conseil d'État"]
KEYWORDS = [
    "chomage", "allocations de chomage", "ONEM", "disponibilite",
    "assurance maladie-invalidite", "INAMI", "incapacite de travail",
    "pension de retraite", "pension de survie", "bonus pension",
    "allocations familiales", "Groeipakket", "AVIQ",
    "accident du travail", "maladie professionnelle", "Fedris",
    "cotisations sociales", "ONSS", "statut social independant",
    "revenu d'integration sociale", "CPAS", "aide sociale"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Loi sur la securite sociale des travailleurs salaries | AR n. 28 du 28 decembre 1944 |
| Loi sur l'assurance obligatoire soins de sante et indemnites | Loi coordonnee du 14 juillet 1994 |
| Loi sur les pensions des travailleurs salaries | AR n. 50 du 24 octobre 1967 |
| Loi sur les accidents du travail | Loi du 10 avril 1971 |
| Loi sur les maladies professionnelles | Lois coordonnees du 3 juin 1970 |
| Loi sur le statut social des independants | AR n. 38 du 27 juillet 1967 |
| Loi sur le RIS et l'aide sociale | Loi du 26 mai 2002 |
| Decret Groeipakket (Flandre) | Decret du 27 avril 2018 |
| Decret AVIQ (Wallonie) | Decret du 3 decembre 2015 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — Moniteur belge pour la legislation, Juridat pour la jurisprudence
2. `top_k=8` — matiere technique avec beaucoup de cas specifiques
3. Allocations familiales regionalisees depuis 2019 : Flandre (Groeipakket), Wallonie (AVIQ), Bruxelles (Iriscare)
4. Les montants et conditions changent regulierement — toujours signaler la date
5. Le tribunal du travail est competent — jurisprudence dans Juridat

## Regles d'or

1. **Zero invention** : ne jamais inventer de montant d'allocation, de taux de cotisation ou de condition d'acces. Ces chiffres sont indexes et changent regulierement.
2. **Double verification** : les montants de securite sociale sont indexes. Toujours verifier la date de la source.
3. **Zero hallucination** : distinguer clairement salaries, independants et fonctionnaires (trois regimes differents).
4. **Humanizer** : la securite sociale concerne des personnes en situation vulnerable. Ton empathique et clair.
5. **Mise a jour** : les montants changent au minimum annuellement. Signaler systematiquement l'annee de reference.
