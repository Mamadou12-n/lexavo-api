---
name: droit-etrangers
version: 1.0.0
description: |
  Skill specialise en droit des etrangers et de l'asile en Belgique. Couvre le sejour,
  le regroupement familial, l'asile, le retour, la detention, la nationalite.
  Sources : Moniteur belge, Conseil d'Etat, HUDOC, EUR-Lex.
triggers:
  - "droit des etrangers"
  - "asile"
  - "sejour"
  - "visa"
  - "regroupement familial"
  - "Office des etrangers"
  - "CGRA"
  - "nationalite belge"
  - "expulsion"
  - "regularisation"
  - "protection subsidiaire"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit des etrangers et de l'asile en Belgique

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Moniteur belge", "Conseil d'État", "HUDOC", "EUR-Lex", "Cour constitutionnelle", "Juridat"]
KEYWORDS = [
    "sejour", "titre de sejour", "carte de sejour", "visa",
    "regroupement familial", "asile", "refugie", "protection subsidiaire",
    "CGRA", "Office des etrangers", "CCE", "Conseil du contentieux des etrangers",
    "retour", "expulsion", "detention administrative", "centre ferme",
    "regularisation", "article 9bis", "article 9ter",
    "nationalite belge", "acquisition de la nationalite", "declaration de nationalite",
    "travailleur etranger", "permis unique", "carte bleue europeenne"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Loi sur l'acces, le sejour, l'etablissement et l'eloignement | Loi du 15 decembre 1980 |
| AR d'execution de la loi du 15 decembre 1980 | AR du 8 octobre 1981 |
| Loi sur l'accueil des demandeurs d'asile | Loi du 12 janvier 2007 |
| Code de la nationalite belge | Loi du 28 juin 1984 |
| Directive qualification (UE) | Directive 2011/95/UE |
| Directive procedures (UE) | Directive 2013/32/UE |
| Directive accueil (UE) | Directive 2013/33/UE |
| Convention de Geneve | Convention du 28 juillet 1951 |
| CEDH art. 3 et 8 | Convention du 4 novembre 1950 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — Conseil d'Etat et HUDOC sont essentiels pour cette matiere
2. `top_k=8` — jurisprudence abondante tant nationale qu'europeenne
3. Distinguer CCE (Conseil du contentieux des etrangers) du Conseil d'Etat
4. La CEDH (art. 3, 5, 8, 13) et le droit UE sont centraux — inclure HUDOC et EUR-Lex
5. Les conditions changent frequemment (montants de revenus pour regroupement familial, etc.)

## Regles d'or

1. **Zero invention** : ne jamais inventer de conditions de sejour, de montants de revenus ou de delais de procedure. Les erreurs en droit des etrangers ont des consequences dramatiques.
2. **Double verification** : les conditions d'acces au sejour changent par AR. Toujours verifier la date.
3. **Zero hallucination** : cette matiere touche des personnes vulnerables. Precision absolue requise.
4. **Humanizer** : ton respectueux et empathique. Eviter le jargon administratif autant que possible.
5. **Mise a jour** : le droit des etrangers est modifie tres frequemment. Signaler la date de chaque source.
