---
name: droit-europeen
version: 1.0.0
description: |
  Skill specialise en droit de l'Union europeenne tel qu'applicable en Belgique. Couvre les
  traites, le marche interieur, la concurrence, les aides d'Etat, le droit institutionnel,
  l'espace de liberte securite justice. Sources : EUR-Lex, HUDOC, Cour constitutionnelle.
triggers:
  - "droit europeen"
  - "droit de l'UE"
  - "Union europeenne"
  - "CJUE"
  - "directive"
  - "reglement europeen"
  - "marche interieur"
  - "aides d'Etat"
  - "concurrence UE"
  - "question prejudicielle CJUE"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit de l'Union europeenne

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["EUR-Lex", "HUDOC", "Cour constitutionnelle", "Moniteur belge", "Conseil d'État"]
KEYWORDS = [
    "TFUE", "TUE", "marche interieur", "libre circulation",
    "directive", "reglement", "decision", "transposition",
    "question prejudicielle", "CJUE", "Tribunal de l'UE",
    "concurrence", "aides d'Etat", "abus de position dominante", "entente",
    "protection des consommateurs", "protection des donnees", "RGPD",
    "espace de liberte securite justice", "mandat d'arret europeen",
    "primauté du droit UE", "effet direct", "responsabilite de l'Etat membre"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Traite sur le fonctionnement de l'UE (TFUE) | Version consolidee 2012/C 326/01 |
| Traite sur l'Union europeenne (TUE) | Version consolidee 2012/C 326/01 |
| Charte des droits fondamentaux de l'UE | 2000/C 364/01 |
| RGPD | Reglement (UE) 2016/679 |
| AI Act | Reglement (UE) 2024/1689 |
| Digital Services Act (DSA) | Reglement (UE) 2022/2065 |
| Digital Markets Act (DMA) | Reglement (UE) 2022/1925 |
| Directive NIS 2 (cybersecurite) | Directive (UE) 2022/2555 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — EUR-Lex est la source principale (5,239 docs dans ChromaDB)
2. `top_k=8` — combiner legislation UE et transposition belge
3. Distinguer reglements (directement applicables) vs directives (transposition necessaire)
4. La Cour constitutionnelle belge applique le droit UE via les articles 10-11 Constitution
5. EUR-Lex contient aussi la jurisprudence de la CJUE et du Tribunal

## Regles d'or

1. **Zero invention** : ne jamais inventer de numero de directive, de reglement ou d'arret de la CJUE. Format attendu : affaire C-XXX/XX.
2. **Double verification** : verifier si la directive a bien ete transposee en droit belge. Consulter EUR-Lex et Moniteur belge.
3. **Zero hallucination** : ne pas confondre la CJUE (Luxembourg) et la CEDH (Strasbourg). Ce sont deux systemes distincts.
4. **Humanizer** : le droit europeen est percu comme abstrait. Le relier aux situations concretes en Belgique.
5. **Mise a jour** : le droit UE evolue rapidement (AI Act, DSA, DMA). Signaler les dates d'entree en vigueur.
