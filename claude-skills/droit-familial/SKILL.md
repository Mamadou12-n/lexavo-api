---
name: droit-familial
version: 1.0.0
description: |
  Skill specialise en droit familial belge. Couvre le divorce, la filiation, l'autorite
  parentale, les obligations alimentaires, les regimes matrimoniaux, la cohabitation legale,
  la protection des mineurs. Sources : Juridat, Moniteur belge, Cour constitutionnelle.
triggers:
  - "droit familial"
  - "droit de la famille"
  - "divorce"
  - "garde des enfants"
  - "pension alimentaire"
  - "autorite parentale"
  - "filiation"
  - "mariage"
  - "cohabitation legale"
  - "adoption"
  - "regime matrimonial"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit familial belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Juridat", "Moniteur belge", "Cour constitutionnelle", "HUDOC"]
KEYWORDS = [
    "divorce", "pension alimentaire", "autorite parentale", "hebergement",
    "filiation", "adoption", "regime matrimonial", "cohabitation legale",
    "obligation alimentaire", "mediation familiale", "protection de la jeunesse",
    "tutelle", "administration provisoire", "consentement mutuel",
    "divorce pour desunion irremédiable", "liquidation-partage"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Code civil — Livre 1 (personnes) | Art. 143 et suivants |
| Code civil — Livre 2.3 (relations familiales) | Nouveau Code civil |
| Loi sur le divorce | Loi du 27 avril 2007 |
| Loi sur la cohabitation legale | Art. 1475-1479 Code civil |
| Code judiciaire — Tribunal de la famille | Art. 1253ter et suivants |
| Loi sur la protection de la jeunesse | Loi du 8 avril 1965 |
| Loi sur l'adoption | Loi du 24 avril 2003 |
| Convention de La Haye (enlevement international) | 25 octobre 1980 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — Juridat est la source principale pour la jurisprudence familiale
2. `top_k=6` standard
3. Prioriser les arrets de la Cour de cassation et de la Cour constitutionnelle
4. Attention aux evolutions recentes (nouveau Code civil Livre 2.3 depuis 2021)
5. Pour les questions CEDH (art. 8 vie privee/familiale), inclure la source HUDOC

## Regles d'or

1. **Zero invention** : ne jamais inventer de montants de pension alimentaire, de jurisprudence ou de bareme. Si un bareme existe (methode Renard, methode Tremmery), le mentionner sans inventer de chiffres.
2. **Double verification** : chaque reference d'arret doit etre verifiee dans ChromaDB.
3. **Zero hallucination** : les situations familiales sont sensibles. Ne jamais donner de conseil definitif, toujours recommander la consultation d'un avocat.
4. **Humanizer** : ton empathique mais professionnel. Eviter le jargon inutile pour les particuliers.
5. **Mise a jour** : le droit familial evolue rapidement (nouveau Code civil). Verifier la date des sources.
