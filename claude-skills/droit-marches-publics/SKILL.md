---
name: droit-marches-publics
version: 1.0.0
description: |
  Skill specialise en droit des marches publics belge. Couvre la passation, l'execution,
  les recours, les concessions, les PPP. Sources : Moniteur belge, Conseil d'Etat, EUR-Lex.
triggers:
  - "marches publics"
  - "adjudication"
  - "procedure negociee"
  - "appel d'offres"
  - "cahier des charges"
  - "soumission"
  - "pouvoir adjudicateur"
  - "concession"
  - "PPP"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit des marches publics belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Moniteur belge", "Conseil d'État", "EUR-Lex", "Juridat", "Cour constitutionnelle"]
KEYWORDS = [
    "marche public", "passation", "execution", "pouvoir adjudicateur",
    "procedure ouverte", "procedure restreinte", "procedure negociee",
    "procedure concurrentielle avec negociation", "dialogue competitif",
    "cahier special des charges", "cahier general des charges",
    "offre economiquement la plus avantageuse", "critere de selection",
    "critere d'attribution", "recours", "suspension", "dommages-interets",
    "concession de services", "concession de travaux", "PPP",
    "sous-traitance", "modification du marche", "penalites"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Loi sur les marches publics | Loi du 17 juin 2016 |
| AR passation des marches publics dans les secteurs classiques | AR du 18 avril 2017 |
| AR regles generales d'execution | AR du 14 janvier 2013 |
| Loi sur les concessions | Loi du 17 juin 2016 |
| Loi recours (standstill et remedies) | Loi du 17 juin 2013 |
| Cahier general des charges (CGC) | Annexe a l'AR du 14 janvier 2013 |
| Directive marches publics (UE) | Directive 2014/24/UE |
| Directive secteurs speciaux (UE) | Directive 2014/25/UE |
| Directive concessions (UE) | Directive 2014/23/UE |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — Conseil d'Etat pour le contentieux, Moniteur belge pour la legislation
2. `top_k=8` — matiere tres technique avec beaucoup de jurisprudence du CE
3. Le Conseil d'Etat est la juridiction principale pour les litiges de passation
4. Les seuils europeens changent tous les deux ans — verifier l'annee
5. Distinguer secteurs classiques vs secteurs speciaux (eau, energie, transport, postal)

## Regles d'or

1. **Zero invention** : ne jamais inventer de seuil de marche public, de delai de standstill ou de numero d'arret du CE.
2. **Double verification** : les seuils europeens changent biannuellement. Toujours verifier la date de la source.
3. **Zero hallucination** : les erreurs en marches publics peuvent entrainer l'annulation d'une procedure. Precision totale requise.
4. **Humanizer** : matiere technique par excellence. Adapter le niveau au public (acheteur public vs soumissionnaire vs juriste).
5. **Mise a jour** : la reglementation evolue regulierement. Signaler les dates des textes cites.
