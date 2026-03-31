---
name: droit-environnement
version: 1.0.0
description: |
  Skill specialise en droit de l'environnement belge. Couvre les permis d'environnement,
  les normes de pollution, la gestion des dechets, l'eau, le sol, le climat, Natura 2000.
  Matiere regionalisee. Sources : Codex Vlaanderen, WalLex, Bruxelles, EUR-Lex.
triggers:
  - "droit environnement"
  - "permis d'environnement"
  - "pollution"
  - "dechets"
  - "eau"
  - "sol"
  - "climat"
  - "Natura 2000"
  - "evaluation des incidences"
  - "sites contamines"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit de l'environnement belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Codex Vlaanderen", "WalLex", "Bruxelles", "Moniteur belge", "EUR-Lex", "Conseil d'État"]
KEYWORDS = [
    "permis d'environnement", "permis unique", "evaluation des incidences",
    "pollution", "emission", "norme de qualite", "sol contamine",
    "dechets", "recyclage", "economie circulaire",
    "eau", "eaux usees", "captage", "zone inondable",
    "Natura 2000", "biodiversite", "especes protegees",
    "climat", "gaz a effet de serre", "certificat vert",
    "nuisances sonores", "qualite de l'air"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| VLAREM I et II (Flandre) | AR du 6 fevrier 1991 et du 1er juin 1995 |
| DGRNE — Code de l'environnement (Wallonie) | Decret du 27 juin 1996 |
| Ordonnance relative aux permis d'environnement (Bruxelles) | Ordonnance du 5 juin 1997 |
| Decret sols (Wallonie) | Decret du 1er mars 2018 |
| Bodemdecreet (Flandre) | Decret du 27 octobre 2006 |
| Ordonnance sols (Bruxelles) | Ordonnance du 5 mars 2009 |
| Loi climat (federale) | Loi du 15 janvier 2024 |
| Directive Habitats (UE) | Directive 92/43/CEE |
| Directive Oiseaux (UE) | Directive 2009/147/CE |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — matiere presque entierement regionalisee
2. `top_k=8` — combiner sources regionales et europeennes
3. Toujours identifier la Region avant de repondre
4. Le droit europeen (directives Habitats, Oiseaux, Eau) s'applique via transposition regionale
5. Le Conseil d'Etat est competent pour le contentieux des permis d'environnement

## Regles d'or

1. **Zero invention** : ne jamais inventer de norme de pollution, de seuil d'emission ou de delai de recours.
2. **Double verification** : verifier la Region applicable et la legislation regionale en vigueur.
3. **Zero hallucination** : trois legislations regionales differentes existent pour chaque matiere environnementale.
4. **Humanizer** : le droit de l'environnement est technique. Rester precis tout en etant comprehensible.
5. **Mise a jour** : les normes environnementales evoluent rapidement (transition climatique). Verifier les dates.
