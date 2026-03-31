---
name: droit-administratif
version: 1.0.0
description: |
  Skill specialise en droit administratif belge. Couvre les actes administratifs, le contentieux
  au Conseil d'Etat, la fonction publique, l'urbanisme, les marches publics, la motivation
  formelle. Sources : Conseil d'Etat, Moniteur belge, Bruxelles, Codex Vlaanderen.
triggers:
  - "droit administratif"
  - "Conseil d'Etat"
  - "acte administratif"
  - "recours en annulation"
  - "suspension"
  - "fonction publique"
  - "urbanisme"
  - "permis"
  - "motivation formelle"
  - "tutelle administrative"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit administratif belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Conseil d'État", "Moniteur belge", "Bruxelles", "Codex Vlaanderen", "GalliLex", "WalLex"]
KEYWORDS = [
    "recours en annulation", "suspension", "extreme urgence",
    "acte administratif", "motivation formelle", "fonction publique",
    "marche public", "urbanisme", "permis d'environnement",
    "tutelle administrative", "decentralisation", "autorite administrative",
    "principe de legalite", "egalite de traitement", "proportionnalite",
    "audi alteram partem", "retrait d'acte", "responsabilite de l'Etat"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Lois coordonnees sur le Conseil d'Etat | AR du 12 janvier 1973 |
| Loi sur la motivation formelle des actes administratifs | Loi du 29 juillet 1991 |
| Loi sur la publicite de l'administration | Loi du 11 avril 1994 |
| CDLD (Code de la democratie locale — Wallonie) | Decret du 22 novembre 2007 |
| Gemeentedecreet (Flandre) | Decret du 15 juillet 2005 |
| Nouvelle loi communale (Bruxelles) | Loi du 24 juin 1988 |
| Statut des agents de l'Etat (AR Camu) | AR du 2 octobre 1937 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — Conseil d'Etat est la source principale
2. `top_k=8` — la jurisprudence du CE est tres abondante
3. Distinguer les trois Regions pour l'urbanisme, l'environnement, la tutelle
4. Les arrets du CE ont un format specifique (numero + date) — verifier les deux
5. Inclure les sources regionales (Bruxelles, Codex Vlaanderen, WalLex, GalliLex) pour les matieres regionalisees

## Regles d'or

1. **Zero invention** : ne jamais inventer de numero d'arret du Conseil d'Etat. Format attendu : arret n. XXX.XXX du JJ/MM/AAAA.
2. **Double verification** : verifier le numero d'arret ET la date dans ChromaDB.
3. **Zero hallucination** : le droit administratif varie entre Regions. Toujours preciser a quelle Region s'applique la reponse.
4. **Humanizer** : le droit administratif est technique. Simplifier pour les citoyens, garder la precision pour les praticiens.
5. **Mise a jour** : la jurisprudence du CE evolue rapidement. Signaler la date des arrets cites.
