---
name: lexavo-emergency
description: >
  Bouton rouge — avocat disponible en 2 heures pour urgences juridiques (49€).
  Déclencher pour : garde à vue, expulsion imminente, licenciement immédiat,
  violence domestique, saisie de biens, accident. Situation critique nécessitant
  une réponse juridique dans l'heure.
category: lexavo
risk: safe
tags: "[emergency, urgent, avocat-urgence, belgique, garde-a-vue]"
date_added: "2026-03-31"
---

# Lexavo Emergency — Avocat en 2h

Service d'urgence juridique : formulaire rapide → notification avocat → rappel en 2h. 49€.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/emergency/categories` | Liste les 7 catégories d'urgence |
| POST | `/emergency/request` | Crée la demande d'urgence |

## Les 7 Catégories

| ID | Label | Priorité |
|----|-------|---------|
| `garde_a_vue` | Garde à vue / Arrestation | CRITICAL |
| `expulsion` | Expulsion imminente | CRITICAL |
| `violence` | Violence domestique | CRITICAL |
| `licenciement` | Licenciement immédiat | HIGH |
| `saisie` | Saisie de biens | HIGH |
| `accident` | Accident / Blessure | HIGH |
| `autre` | Autre urgence juridique | MEDIUM |

## Paramètres

```json
{
  "category": "garde_a_vue",
  "description": "Mon fils vient d'être arrêté et placé en garde à vue à Bruxelles",
  "phone": "+32470123456",
  "city": "Bruxelles"
}
```

## Structure de la réponse

```json
{
  "request_id": "URG-20260331-0001",
  "category": "garde_a_vue",
  "priority": "critical",
  "status": "pending",
  "price_cents": 4900,
  "estimated_callback": "Dans les 2 heures",
  "disclaimer": "Service de mise en relation urgente."
}
```

## Tarification

- **Prix fixe** : 49€ par demande
- **Délai garanti** : Rappel dans les 2 heures
- **Paiement** : Via Stripe (intégration `stripe-integration`)

## Skills juridiques intégrés

- `droit-penal` → garde à vue, arrestation, assistance judiciaire
- `droit-travail` → licenciement immédiat, représailles
- `droit-immobilier` → expulsion, saisie immobilière
- `droit-fondamentaux` → droits fondamentaux en garde à vue (art. 6 CEDH)

## Numéros d'urgence légaux (information)

| Service | Numéro |
|---------|--------|
| Police | 101 |
| Aide Juridique de Première Ligne | 0800/12.500 |
| SOS Violence Conjugale | 0800/30.030 |

⚠️ Lexavo Emergency est un service de MISE EN RELATION.
En cas de danger immédiat pour la vie, appeler le 101 ou le 112 en priorité.
