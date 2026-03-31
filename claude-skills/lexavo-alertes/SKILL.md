---
name: lexavo-alertes
description: >
  Alertes législatives personnalisées par domaine juridique. Déclencher pour :
  s'abonner aux changements de loi, suivre l'actualité juridique belge,
  recevoir des notifications sur les nouvelles CCT, lois, arrêtés royaux.
  8 domaines : travail, bail, fiscal, famille, entreprise, social, immobilier, environnement.
category: lexavo
risk: safe
tags: "[alertes, legislation, moniteur-belge, actualite-juridique, belgique]"
date_added: "2026-03-31"
---

# Lexavo Alertes — Veille Législative Belge

Système d'alertes personnalisées sur les changements législatifs belges par domaine.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/alerts/domains` | Liste les 8 domaines disponibles |
| POST | `/alerts/preferences` | Sauvegarde les préférences utilisateur |
| GET | `/alerts/feed` | Fil d'alertes personnalisé (limit=10) |

## Les 8 Domaines

| ID | Label | Exemples de changements |
|----|-------|------------------------|
| `travail` | Droit du travail | CCT, salaire minimum, télétravail |
| `bail` | Droit du bail | Indexation loyers, garantie locative |
| `fiscal` | Droit fiscal | IPP, ISOC, TVA, barèmes annuels |
| `famille` | Droit familial | Pension alimentaire, garde partagée |
| `entreprise` | Droit des entreprises | CSA, RGPD, droit de la concurrence |
| `social` | Sécurité sociale | ONEM, INAMI, pensions, allocations |
| `immobilier` | Droit immobilier | Urbanisme, copropriété, permis |
| `environnement` | Droit environnement | Permis, normes, énergie |

## Structure d'une alerte

```json
{
  "id": 1,
  "domain": "travail",
  "title": "Nouvelle CCT sur le télétravail structurel",
  "summary": "Le CNT a adopté la CCT n°149/2...",
  "date": "2026-03-15",
  "source": "Moniteur belge",
  "url": "https://www.ejustice.just.fgov.be/..."
}
```

## Sources surveillées

- **Moniteur belge** (ejustice.just.fgov.be) — Lois, AR, AM
- **CNT** (cnt.be) — CCT nationales et sectorielles
- **SPF Finances** (finances.belgium.be) — Circulaires fiscales
- **APD** (autoriteprotectiondonnees.be) — Décisions et lignes directrices
- **ONEM** (onem.be) — Règlements chômage et activation

## Intégration NotebookLM — Digest hebdomadaire

```python
from notebooklm import NotebookLMClient

async def generate_weekly_digest(domains: list, user_id: int):
    async with await NotebookLMClient.from_storage() as client:
        # Créer un notebook "Veille juridique semaine X"
        nb = await client.notebooks.create(f"Veille Lexavo — Semaine {week_number}")

        # Ajouter les URLs des nouvelles publications législatives
        for alert in get_new_alerts(domains):
            if alert.url:
                await client.sources.add_url(nb.id, alert.url)

        # Générer un résumé structuré
        result = await client.chat.ask(nb.id,
            "Résume les changements législatifs importants de cette semaine")

        # Optionnel : générer podcast de veille
        await client.artifacts.generate_audio(nb.id,
            instructions="Résumé professionnel pour juriste belge")

        return result.answer
```

## Skills invoqués dynamiquement

Selon le domaine de l'alerte :
- `droit-travail` → domaine `travail`
- `droit-fiscal` → domaine `fiscal`
- `droit-immobilier` → domaines `bail` + `immobilier`
- `droit-commercial` → domaine `entreprise`
- `droit-securite-sociale` → domaine `social`
- `droit-fondamentaux` → domaine `entreprise` (RGPD)

## Roadmap

- **Phase 1** (actuel) : Fil statique de démonstration
- **Phase 2** : Scraping automatique Moniteur belge + CNT
- **Phase 3** : Notifications push Expo (React Native)
- **Phase 4** : Digest email/podcast hebdomadaire via NotebookLM
