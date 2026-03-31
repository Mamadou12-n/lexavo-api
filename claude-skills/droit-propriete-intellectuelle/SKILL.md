---
name: droit-propriete-intellectuelle
version: 1.0.0
description: |
  Skill specialise en propriete intellectuelle belge et Benelux. Couvre les marques (BOIP),
  brevets, droits d'auteur, dessins et modeles, secrets d'affaires, noms de domaine.
  Sources : Moniteur belge, EUR-Lex, Juridat, FSMA.
triggers:
  - "propriete intellectuelle"
  - "marque"
  - "brevet"
  - "droit d'auteur"
  - "contrefacon"
  - "BOIP"
  - "dessin et modele"
  - "secret d'affaires"
  - "licence"
  - "copyright"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
---

# Propriete intellectuelle belge

## Sources prioritaires dans ChromaDB

```python
SOURCE_FILTER = ["Moniteur belge", "EUR-Lex", "Juridat", "Cour constitutionnelle"]
KEYWORDS = [
    "droit d'auteur", "droits voisins", "marque", "marque Benelux",
    "brevet", "brevet europeen", "contrefacon", "concurrence deloyale",
    "dessin et modele", "secret d'affaires", "licence",
    "nom de domaine", "indication geographique", "obtention vegetale",
    "droit sui generis bases de donnees", "BOIP",
    "action en cessation", "saisie-contrefacon"
]
```

## Legislation de reference

| Texte | Reference |
|-------|-----------|
| Code de droit economique — Livre XI (PI) | CDE Livre XI |
| Convention Benelux en matiere de PI | Convention du 25 fevrier 2005 |
| Loi sur les brevets d'invention | Loi du 28 mars 1984 |
| Convention sur le brevet europeen (CBE) | Convention de Munich 1973 |
| Directive droit d'auteur dans le marche unique numerique | Directive (UE) 2019/790 |
| Directive secrets d'affaires | Directive (UE) 2016/943 |
| Reglement marque de l'UE | Reglement (UE) 2017/1001 |

## Strategie RAG

1. Filtrer par `SOURCE_FILTER` — EUR-Lex pour le cadre europeen, Juridat pour la jurisprudence nationale
2. `top_k=6` standard
3. Distinguer marque Benelux (BOIP) vs marque UE (EUIPO) vs marque internationale (OMPI)
4. Le droit d'auteur belge est dans le Livre XI du CDE
5. Les brevets : systeme national + europeen (OEB) + brevet unitaire europeen

## Regles d'or

1. **Zero invention** : ne jamais inventer de numero de marque, de brevet ou de reference BOIP/EUIPO.
2. **Double verification** : verifier la validite des references dans les registres officiels si possible.
3. **Zero hallucination** : les delais en PI sont stricts (delais de depot, d'opposition). Ne jamais les inventer.
4. **Humanizer** : la PI est une matiere de specialistes. Adapter le ton selon que le demandeur est un createur, un entrepreneur ou un juriste.
5. **Mise a jour** : le brevet unitaire europeen est en vigueur depuis juin 2023. Le signaler pour les questions de brevets.
