---
name: lexavo-match
description: >
  Mise en relation intelligente avec avocats partenaires belges. Déclencher pour :
  trouver un avocat, chercher un spécialiste en droit X à ville Y,
  recommander les 3 meilleurs avocats selon la situation juridique décrite.
  Utilise la détection automatique de branche + base avocats Lexavo.
category: lexavo
risk: safe
tags: "[match, avocats, mise-en-relation, belgique, barreaux]"
date_added: "2026-03-31"
---

# Lexavo Match — Mise en Relation Avocat

Analyse la situation juridique et propose les 3 avocats les mieux adaptés
parmi les partenaires Lexavo (barreaux de Bruxelles, Liège, Gand, Anvers, etc.)

## Endpoint API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/match/find` | Trouve les avocats adaptés |

## Paramètres

```json
{
  "description": "Mon propriétaire refuse de rendre ma garantie locative de 1500€",
  "city": "Bruxelles",
  "language": "fr",
  "budget": "normal"
}
```

## Structure de la réponse

```json
{
  "detected_branch": "droit_immobilier",
  "detected_specialty": "Droit immobilier",
  "matches": [
    {
      "lawyer_id": 1,
      "name": "Me Sophie Lambert",
      "bar": "Barreau de Bruxelles",
      "city": "Bruxelles",
      "specialties": ["Droit immobilier", "Droit du bail"],
      "match_score": 0.92,
      "match_reason": "Spécialisée en droit du bail, 12 ans d'expérience"
    }
  ],
  "total_matches": 3,
  "disclaimer": "Mise en relation informative. L'avocat reste indépendant."
}
```

## Algorithme de matching

1. Détection de la branche du droit (via Shield detect_contract_type)
2. Filtrage par ville si précisée
3. Tri par score de match (spécialité + rating + disponibilité)
4. Retour des 3 meilleurs

## Branches et spécialités mappées

| Branche | Spécialité avocat |
|---------|------------------|
| droit_travail | Droit social |
| droit_immobilier | Droit immobilier |
| droit_familial | Droit familial |
| droit_fiscal | Droit fiscal |
| droit_commercial | Droit des affaires |
| droit_penal | Droit pénal |

## Barreaux belges couverts

- Barreau de Bruxelles (OBFG + OVB)
- Barreau de Liège-Huy
- Barreau de Gand
- Barreau d'Anvers
- Barreau de Mons
- Barreau de Namur

## Skills juridiques intégrés

Invoquer le skill de la branche détectée pour enrichir le contexte du match.
Invoquer `humanizer` sur la réponse finale.

## Intégration lexavo-emergency

Si urgence détectée → rediriger vers `lexavo-emergency` (avocat en 2h).
