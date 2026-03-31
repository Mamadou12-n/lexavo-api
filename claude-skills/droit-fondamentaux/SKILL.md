---
name: droit-fondamentaux
version: 1.0.0
description: |
  Skill specialise en droits fondamentaux. Couvre la Constitution belge, la CEDH, la Charte
  des droits fondamentaux de l'UE, les droits economiques et sociaux, la non-discrimination,
  la protection des donnees (RGPD). Sources : HUDOC, EUR-Lex, Cour constitutionnelle.
triggers:
  - "droits fondamentaux"
  - "Constitution"
  - "CEDH"
  - "Charte des droits fondamentaux"
  - "discrimination"
  - "liberte d'expression"
  - "vie privee"
  - "RGPD"
  - "protection des donnees"
  - "egalite"
  - "APD"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Droits fondamentaux

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["HUDOC", "EUR-Lex", "Cour constitutionnelle", "Moniteur belge", "APD", "Juridat"]
KEYWORDS = [
    "Constitution belge", "droits fondamentaux", "CEDH",
    "Charte des droits fondamentaux UE", "droit a la vie", "interdiction de la torture",
    "liberte d'expression", "liberte de reunion", "liberte de religion",
    "droit a la vie privee", "article 8 CEDH", "protection des donnees",
    "RGPD", "APD", "non-discrimination", "egalite",
    "droit a un proces equitable", "article 6 CEDH",
    "recours effectif", "article 13 CEDH",
    "Cour constitutionnelle", "question prejudicielle", "recours en annulation"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Constitution belge | Texte coordonne du 17 fevrier 1994 |
| Convention europeenne des droits de l'homme | Convention du 4 novembre 1950 |
| Charte des droits fondamentaux de l'UE | 2000/C 364/01 |
| RGPD | Reglement (UE) 2016/679 |
| Loi sur l'APD | Loi du 3 decembre 2017 |
| Loi anti-discrimination | Loi du 10 mai 2007 |
| Loi genre | Loi du 10 mai 2007 |
| Loi antiracisme | Loi du 30 juillet 1981 |
| Loi speciale sur la Cour constitutionnelle | Loi speciale du 6 janvier 1989 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — HUDOC est la source principale pour la CEDH
2. `top_k=8` — les droits fondamentaux touchent toutes les branches du droit
3. La Cour constitutionnelle belge est competente pour controler le respect des articles 10, 11, 24 de la Constitution + CEDH et Charte UE via combinaison
4. L'APD (Autorite de protection des donnees) rend des decisions en matiere RGPD
5. Distinguer CEDH (Strasbourg) vs CJUE (Luxembourg) vs Cour constitutionnelle (Bruxelles)

## Regles d'or

1. **Zero invention** : ne jamais inventer de reference d'arret de la Cour europeenne des droits de l'homme ou de la Cour constitutionnelle.
2. **Double verification** : les arrets HUDOC ont un format ECLI specifique. Verifier dans ChromaDB.
3. **Zero hallucination** : les droits fondamentaux sont des matieres sensibles. Precision absolue dans les references.
4. **Humanizer** : cette matiere concerne souvent des personnes dont les droits sont menaces. Ton respectueux et accessible.
5. **Mise a jour** : la jurisprudence de la CEDH et de la Cour constitutionnelle evolue constamment. Signaler les dates.
