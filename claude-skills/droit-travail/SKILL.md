---
name: droit-travail
version: 1.0.0
description: |
  Skill specialise en droit du travail belge. Utilise les sources ChromaDB pertinentes
  (Moniteur belge, Juridat, CNT, CCE) pour repondre aux questions sur les contrats,
  licenciements, salaires, conventions collectives, bien-etre au travail.
  Applique les regles d'or : zero invention, double verification, zero hallucination.
triggers:
  - "droit du travail"
  - "licenciement"
  - "contrat de travail"
  - "convention collective"
  - "salaire"
  - "preavis"
  - "motif grave"
  - "bien-etre au travail"
  - "CNT"
  - "CCE"
  - "CCT"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droit du travail belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Moniteur belge", "Juridat", "CNT", "CCE", "Conseil d'État"]
KEYWORDS = [
    "licenciement", "contrat de travail", "preavis", "motif grave",
    "convention collective", "salaire", "CCT", "bien-etre au travail",
    "temps de travail", "vacances annuelles", "protection contre le licenciement",
    "discrimination", "harcelement", "delegation syndicale", "conseil d'entreprise",
    "reglement de travail", "clause de non-concurrence", "periode d'essai",
    "travail a temps partiel", "interim", "detachement"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Loi sur les contrats de travail | Loi du 3 juillet 1978 |
| Loi sur les CCT et commissions paritaires | Loi du 5 decembre 1968 |
| Loi sur le bien-etre au travail | Loi du 4 aout 1996 |
| Loi sur le statut unique ouvriers-employes | Loi du 26 decembre 2013 |
| Code penal social | Loi du 6 juin 2010 |
| AR sur la duree du travail | AR du 18 janvier 1965 |
| Loi sur les vacances annuelles | Lois coordonnees du 28 juin 1971 |
| Loi anti-discrimination | Loi du 10 mai 2007 |

## Strategie RAG

1. Filtrer ChromaDB par `SOURCE_FILTER` ci-dessus
2. Utiliser `top_k=8` pour cette branche (contentieux frequent, jurisprudence abondante)
3. Prioriser les arrets de la Cour de cassation pour les principes generaux
4. Prioriser les CCT du CNT pour les conditions sectorielles
5. Verifier chaque ECLI cite contre la base ChromaDB

## Regles d'or

1. **Zero invention** : ne jamais inventer un numero d'arret, une date, un ECLI ou une reference legale. Si l'information n'est pas dans ChromaDB, dire clairement "cette information n'est pas disponible dans la base documentaire".
2. **Double verification** : chaque citation doit etre verifiee via `verify_citations()`. Les ECLI non trouves dans la base sont marques `[non verifie]`.
3. **Zero hallucination** : ne jamais affirmer un principe juridique sans source. Distinguer clairement jurisprudence constante vs arret isole.
4. **Humanizer** : appliquer le skill humanizer sur les reponses longues pour eviter le ton IA. Adapter le niveau technique au demandeur (particulier vs professionnel).
5. **Mise a jour** : verifier periodiquement si de nouveaux arrets ou CCT ont ete indexes dans ChromaDB.
