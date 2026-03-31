---
name: droit-immobilier
version: 1.0.0
description: |
  Skill specialise en droit immobilier belge. Couvre le bail, la copropriete, la vente
  immobiliere, l'urbanisme, les permis de construire, le cadastre, les droits reels.
  Sources : Moniteur belge, Bruxelles, Codex Vlaanderen, WalLex, Juridat.
triggers:
  - "droit immobilier"
  - "bail"
  - "location"
  - "copropriete"
  - "vente immobiliere"
  - "permis de construire"
  - "urbanisme"
  - "cadastre"
  - "hypotheque"
  - "servitude"
  - "emphyteose"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit immobilier belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Moniteur belge", "Bruxelles", "Codex Vlaanderen", "WalLex", "GalliLex", "Juridat"]
KEYWORDS = [
    "bail", "bail d'habitation", "bail commercial", "bail a ferme",
    "copropriete", "syndic", "assemblee generale des coproprietaires",
    "vente immobiliere", "compromis de vente", "acte authentique",
    "permis d'urbanisme", "permis d'environnement", "certificat PEB",
    "cadastre", "precompte immobilier", "hypotheque",
    "emphyteose", "superficie", "usufruit", "servitude",
    "expropriation", "droit de preemption"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Nouveau Code civil — Livre 3 (biens) | Loi du 4 fevrier 2020 |
| Bail d'habitation — Region wallonne | Decret du 15 mars 2018 |
| Bail d'habitation — Region bruxelloise | Ordonnance du 27 juillet 2017 |
| Bail d'habitation — Region flamande (Vlaams Woninghuurdecreet) | Decret du 9 novembre 2018 |
| Loi sur la copropriete | Art. 3.84-3.100 nouveau CC |
| CoBAT (Bruxelles — urbanisme) | Ordonnance du 29 aout 1991 |
| CoDT (Wallonie — urbanisme) | Decret du 20 juillet 2016 |
| VCRO (Flandre — urbanisme) | Decret du 27 mars 2009 |
| Loi hypothecaire | Loi du 16 decembre 1851 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — matiere fortement regionalisee, inclure les trois Regions
2. `top_k=8` — combiner sources federales et regionales
3. Le bail d'habitation est entierement regionalise depuis 2014 — toujours demander la Region
4. L'urbanisme depend de trois codes differents (CoBAT, CoDT, VCRO)
5. Le Livre 3 du nouveau CC a reforme le droit des biens depuis le 1er septembre 2021

## Regles d'or

1. **Zero invention** : ne jamais inventer de montant de loyer, d'indice de reference ou de delai de preavis. Ces donnees varient par Region et par annee.
2. **Double verification** : toujours verifier quelle Region s'applique avant de repondre sur le bail ou l'urbanisme.
3. **Zero hallucination** : les regles varient enormement entre Bruxelles, Wallonie et Flandre. Ne jamais generaliser.
4. **Humanizer** : le droit immobilier concerne beaucoup de particuliers. Langage clair et accessible.
5. **Mise a jour** : les indices de reference des loyers et le precompte immobilier changent chaque annee. Signaler l'annee des donnees.
