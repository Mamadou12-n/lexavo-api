---
name: lexavo-defend
description: >
  "Je veux agir" — Contestation, recours, mise en demeure.
  Detecte automatiquement le type de probleme, genere le document legal.
  Amendes, bail, travail, huissier, consommation, social, scolaire, fiscal.
  ZERO invention, ZERO hallucination, ZERO fausse source.
category: lexavo
risk: safe
tags: "[defend, contestation, amende, mise en demeure, recours, belgique, document, lettre]"
date_added: "2026-04-01"
---

# Lexavo Defend — "Je veux agir"

Un seul bouton. L'utilisateur decrit sa situation en langage naturel.
Lexavo detecte automatiquement le type de probleme et genere le document adapte.

## Regle INVIOLABLE
- **ZERO invention** — chaque article cite DOIT exister dans la base RAG
- **ZERO hallucination** — si pas trouve, dire "information non disponible"
- **ZERO fausse source** — chaque reference est verifiable

## Endpoints API

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/defend/categories` | Liste des 8 categories |
| POST | `/defend/detect` | Detection auto du type de situation |
| POST | `/defend/analyze` | Analyse complete + generation document |

## 8 Categories

| ID | Label | Exemples |
|----|-------|----------|
| amende | Contester une amende | Radar, STIB/TEC, SAC, stationnement |
| consommation | Probleme consommation | Remboursement, clause abusive, facture |
| bail | Probleme logement | Caution, proprietaire, insalubrite |
| travail | Conflit travail | Licenciement, accident, harcelement |
| huissier | Lettre huissier | Reponse, saisie, opposition |
| social | Droits sociaux | Mutuelle, CPAS, allocations, chomage |
| scolaire | Probleme scolaire | Exclusion, inscription, recours |
| fiscal | Contestation fiscale | SPF Finances, taxe communale |

## Flow

```
Utilisateur decrit sa situation
         |
IA detecte le type (amende/bail/travail...)
         |
Analyse juridique + sources RAG
         |
Genere le document (contestation/mise en demeure/recours)
         |
L'utilisateur telecharge et envoie
```

## Requete POST /defend/analyze

```json
{
  "description": "J'ai recu une amende de 58€ pour stationnement mais il n'y avait aucun panneau d'interdiction",
  "category": null,
  "region": "bruxelles",
  "user_name": "Jean Dupont",
  "user_address": "Rue de la Loi 16, 1000 Bruxelles"
}
```

## Reponse

```json
{
  "detection": {"category": "amende", "confidence": 0.85},
  "situation_analysis": "Analyse de votre situation...",
  "applicable_law": [
    {"article": "Art. 12 AR 01/12/1975", "content": "...", "source": "Moniteur belge"}
  ],
  "contestation_possible": true,
  "success_probability": "haute",
  "document_type": "contestation",
  "document_text": "Madame, Monsieur, Par la presente...",
  "recipient": "Parquet de police de Bruxelles",
  "deadline": "30 jours a compter de la notification",
  "next_steps": ["Envoyer par recommande", "Garder une copie"],
  "disclaimer": "Lexavo est un assistant juridique. Il ne remplace pas un avocat."
}
```

## Humanizer
Toutes les reponses passent par le humanizer pour un ton naturel.
Le document formel garde son ton juridique (pas humanise).

## Integration avec les branches du droit
Chaque categorie est mappee a une branche :
- amende → droit_penal
- consommation → droit_commercial
- bail → droit_immobilier
- travail → droit_travail
- huissier → droit_civil
- social → droit_securite_sociale
- scolaire → droit_administratif
- fiscal → droit_fiscal
