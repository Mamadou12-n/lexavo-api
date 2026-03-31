---
name: lexavo-contrats
description: >
  Générer des contrats types belges en PDF avec branding Lexavo.
  Déclencher pour : générer un bail, contrat de travail, mise en demeure,
  contrat de vente, CGV, convention de cohabitation, contrat de prêt.
  Remplit les variables et génère HTML + PDF WeasyPrint.
category: lexavo
risk: safe
tags: "[contrats, pdf, templates, bail, travail, belgique]"
date_added: "2026-03-31"
---

# Lexavo Contrats — Templates Juridiques Belges

9 templates de contrats prêts à l'emploi, adaptés au droit belge par région.

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/contracts/templates` | Liste tous les templates (filtres: category, region) |
| GET | `/contracts/{id}` | Détail d'un template + variables requises |
| POST | `/contracts/{id}/generate` | Génère le contrat HTML rempli |

## Templates disponibles

| ID | Nom | Région | Catégorie |
|----|-----|--------|-----------|
| `bail_bruxelles` | Contrat de bail résidentiel (Bruxelles) | bruxelles | immobilier |
| `bail_wallonie` | Contrat de bail résidentiel (Wallonie) | wallonie | immobilier |
| `bail_flandre` | Huurcontract (Flandre) | flandre | immobilier |
| `contrat_travail_cdi` | Contrat de travail CDI | national | travail |
| `mise_en_demeure` | Lettre de mise en demeure | national | civil |
| `vente_entre_particuliers` | Contrat de vente entre particuliers | national | civil |
| `contrat_pret` | Contrat de prêt entre particuliers | national | civil |
| `cgv_independant` | CGV pour indépendant | national | commercial |
| `convention_cohabitation` | Convention de cohabitation légale | national | famille |

## Génération d'un contrat

```json
POST /contracts/bail_bruxelles/generate
{
  "variables": {
    "bailleur_nom": "Jean Dupont",
    "locataire_nom": "Marie Martin",
    "adresse_bien": "Rue de la Loi 1, 1000 Bruxelles",
    "loyer": "850",
    "date_entree": "2026-05-01"
  }
}
```

## Génération PDF

Utilise WeasyPrint avec branding Lexavo :
- Couleur principale : `#E85D26` (orange Lexavo)
- Couleur secondaire : `#1C2B3A` (navy)
- Police : System UI / Helvetica
- Format : A4, marges 2cm

## Skills juridiques intégrés

- `droit-immobilier` → pour les baux (règles régionales, garantie locative)
- `droit-travail` → pour les contrats CDI (CCT applicable, période d'essai)
- `droit-civil` → pour mise en demeure, vente, prêt
- `droit-commercial` → pour CGV (mentions légales obligatoires B2B)

## Intégration NotebookLM

Pour enrichir les templates avec de la jurisprudence récente :
```python
# Créer notebook avec les arrêts récents sur le type de contrat
# Extraire les clauses recommandées / à éviter
# Mettre à jour le template automatiquement
```

## Disclaimer légal obligatoire

Tout contrat généré inclut :
> "Modèle type. Consultez un notaire ou un avocat avant signature pour les contrats impliquant des enjeux importants."
