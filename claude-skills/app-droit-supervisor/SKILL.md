---
name: app-droit-supervisor
description: Chef d'orchestre permanent du projet App Droit Belgique. Supervise l'utilisation de TOUS les skills disponibles, dans l'ordre exact, avec Ralph et GSD actifs sur chaque tâche. Mis à jour chaque lundi matin.
version: 2.1.0
author: App Droit Project
date: 2026-03-30
last_updated: 2026-03-30
next_update: 2026-04-06
triggers:
  - "droit"
  - "app droit"
  - "supervise"
  - "quel skill"
  - "par où commencer"
  - "prochaine étape"
  - "chef d'orchestre"
  - "supervisor"
  - "juridat"
  - "juridique"
  - "arrêt"
  - "jugement"
  - "avocat"
  - "barreau"
  - "jurisprudence"
  - "scraping juridique"
  - "base juridique"
  - "RAG juridique"
  - "phase 1"
  - "phase 2"
  - "phase 3"
  - "phase 4"
  - "phase 5"
---

# APP DROIT SUPERVISOR v2.1
## Chef d'Orchestre — 300+ Skills + 15 Branches du Droit + Humanizer — Ordre Strict

> **AUTO-EXÉCUTION** : Ce skill s'active automatiquement dès que le mot "droit" ou tout autre déclencheur apparaît. Aucune confirmation requise — la machine démarre immédiatement selon le protocole ci-dessous.

---

## CHARTE DES RÈGLES ABSOLUES
### Vérifier AVANT chaque tâche, sans exception

- [ ] **RÈGLE 1 — Mémoire à jour** : La mémoire sera mise à jour APRÈS cette tâche. Chaque lundi matin, ce skill lui-même est mis à jour.
- [ ] **RÈGLE 2 — ZÉRO INVENTION** : Aucune donnée inventée. Chiffres, arrêts, stats, projections — tout doit venir d'une source réelle vérifiée. Si inconnu → "je ne sais pas" + source où trouver.
- [ ] **RÈGLE 3 — GSD vérifie tout** : Toute information venant d'un agent passe par `gsd-2-agent-framework` avant utilisation.
- [ ] **RÈGLE 4 — Skills obligatoires** : Chaque domaine touché, même à 1%, déclenche le skill correspondant. Aucun skill ignoré.
- [ ] **RÈGLE 5 — Ralph sur chaque tâche** : `ralph` est invoqué sur chaque tâche pour garantir la complétion. La tâche ne s'arrête pas tant qu'elle n'est pas vérifiée et validée.

Si une règle n'est pas cochée → **STOP TOTAL**. Corriger avant de continuer.

---

## PROTOCOLE D'EXÉCUTION — Ordre strict pour chaque tâche

```
ÉTAPE 0 : Vérifier les 5 règles de la Charte
ÉTAPE 1 : Invoquer ralph → garantir la complétion
ÉTAPE 2 : Identifier la phase du projet (1 à 5)
ÉTAPE 3 : Invoquer TOUS les skills de la phase, dans l'ordre
ÉTAPE 4 : Invoquer GSD → vérifier tous les outputs
ÉTAPE 5 : Invoquer doublecheck → valider avant livraison
ÉTAPE 6 : Mettre à jour la mémoire
ÉTAPE 7 : Si lundi → mettre à jour ce skill (version + date)
```

---

## LES 9 PLUGINS ACTIFS — Catalogue complet

### PLUGIN 1 : SUPERPOWERS
Intervient sur : planification, développement, debugging, review, tests, documentation
Tous les sous-skills doivent être utilisés selon leur rôle :

| Skill | Rôle spécifique dans App Droit |
|---|---|
| `superpowers:write-plan` | Planifier chaque phase avant de coder |
| `superpowers:execute-plan` | Exécuter le plan étape par étape |
| `superpowers:brainstorm` / `superpowers:brainstorming` | Générer des idées sur architecture, UX, features |
| `superpowers:writing-plans` | Rédiger les plans techniques détaillés |
| `superpowers:writing-skills` | Rédiger documentation et guides utilisateur |
| `superpowers:test-driven-development` | Écrire les tests AVANT le code |
| `superpowers:systematic-debugging` | Débugger méthodiquement |
| `superpowers:subagent-driven-development` | Déléguer des tâches à des sous-agents |
| `superpowers:requesting-code-review` | Demander une review après chaque feature |
| `superpowers:receiving-code-review` | Appliquer les feedbacks de review |
| `superpowers:code-reviewer` | Reviewer le code produit |
| `superpowers:dispatching-parallel-agents` | Lancer plusieurs agents en parallèle |
| `superpowers:executing-plans` | Suivre l'exécution étape par étape |
| `superpowers:finishing-a-development-branch` | Finaliser proprement chaque branche |
| `superpowers:using-git-worktrees` | Isoler les branches de travail |
| `superpowers:verification-before-completion` | Vérifier AVANT de déclarer une tâche terminée |
| `superpowers:using-superpowers` | Guide d'utilisation optimal des superpowers |

### PLUGIN 2 : ENGINEERING
Intervient sur : architecture, code, déploiement, infrastructure
Tous les sous-skills :

| Skill | Rôle spécifique dans App Droit |
|---|---|
| `engineering:architecture` | Architecture RAG, microservices, API |
| `engineering:system-design` | Design système complet (scraper + RAG + API + app) |
| `engineering:code-review` | Review chaque PR |
| `engineering:testing-strategy` | Stratégie de tests unitaires + intégration |
| `engineering:debug` | Debug des pipelines de scraping et RAG |
| `engineering:documentation` | Documenter l'API FastAPI et le RAG |
| `engineering:deploy-checklist` | Checklist avant chaque déploiement |
| `engineering:tech-debt` | Identifier et gérer la dette technique |
| `engineering:standup` | Suivi quotidien du progrès |
| `engineering:incident-response` | Gérer les incidents en production |

### PLUGIN 3 : FRONTEND-DESIGN
Intervient sur : UI/UX, design système, accessibilité
Tous les sous-skills :

| Skill | Rôle spécifique dans App Droit |
|---|---|
| `frontend-design:frontend-design` | Architecture frontend React Native |
| `design:design-system` | Créer le design system de l'app |
| `design:ux-copy` | Rédiger les textes UI (boutons, messages, onboarding) |
| `design:user-research` | Recherche utilisateurs avocats belges |
| `design:research-synthesis` | Synthétiser les retours utilisateurs |
| `design:design-handoff` | Préparer les specs pour le développement |
| `design:design-critique` | Critiquer et améliorer les maquettes |
| `design:accessibility-review` | Vérifier l'accessibilité (WCAG) |
| `stitch-design-taste` | Générer le DESIGN.md premium anti-générique |
| `stitch-ui-design` | Générer des screens UI via Google Stitch |
| `stitch-loop` | Itérer sur le design en boucle |
| `ui-ux-pro-max` | Standards UI/UX professionnels |
| `premium-frontend-ui` | Qualité frontend premium |
| `penpot-uiux-design` | Maquettes Penpot |

### PLUGIN 4 : MARKETING
Intervient sur : acquisition, contenu, SEO, campagnes, analytics
Tous les sous-skills :

| Skill | Rôle spécifique dans App Droit |
|---|---|
| `marketing:campaign-plan` | Planifier les campagnes d'acquisition avocats |
| `marketing:content-creation` | Créer contenu juridique pour le blog |
| `marketing:draft-content` | Rédiger articles, posts LinkedIn, emails |
| `marketing:email-sequence` | Séquences email onboarding + nurturing avocats |
| `marketing:seo-audit` | Audit SEO du site App Droit |
| `marketing:performance-report` | Analyser les performances marketing |
| `marketing:competitive-brief` | Brief concurrentiel Vikk, Lawhive, SuperLawyer |
| `marketing:brand-review` | Review de la marque App Droit |
| `gtm-0-to-1-launch` | Trouver les 10 premiers avocats clients |
| `gtm-positioning-strategy` | Positionnement "droit belge FR/NL/EN" |
| `gtm-product-led-growth` | Stratégie croissance par le produit |
| `gtm-technical-product-pricing` | Pricing technique et packaging |
| `gtm-partnership-architecture` | Partenariats barreaux, éditeurs juridiques |
| `gtm-0-to-1-launch` | Premier lancement 0 → 1 |
| `gtm-enterprise-account-planning` | Grands cabinets d'avocats |
| `gtm-operating-cadence` | Cadence opérationnelle marketing |
| `gtm-board-and-investor-communication` | Communication investisseurs |
| `launch-strategy` | Stratégie de lancement complète |
| `growth-engine` | Moteur de croissance durable |
| `viral-strategy-engine` | Stratégie virale pour avocats |
| `viral-hook-creator` | Hooks viraux pour LinkedIn juridique |
| `content-strategy` | Stratégie contenu droit belge |
| `content-creator` | Création contenu multiformat |
| `content-marketer` | Distribution et amplification |
| `seo-audit` | SEO technique et contenu |
| `programmatic-seo` | SEO programmatique sur mots-clés juridiques |
| `cold-email` | Outreach direct avocats |
| `lead-magnets` | Aimants à prospects (guides juridiques gratuits) |
| `lead-research-assistant` | Recherche prospects avocats |
| `social-content` | Contenu réseaux sociaux |
| `linkedin-automation` | Automatisation LinkedIn avocats |
| `paid-ads` | Campagnes publicitaires |

### PLUGIN 5 : DATA
Intervient sur : analyse données, dashboards, SQL, visualisations
Tous les sous-skills :

| Skill | Rôle spécifique dans App Droit |
|---|---|
| `data:analyze` | Analyser les données scrapées de Juridat |
| `data:explore-data` | Explorer les datasets juridiques |
| `data:validate-data` | Valider la qualité des données scrapées |
| `data:write-query` | Écrire les requêtes SQL sur pgvector |
| `data:sql-queries` | Requêtes complexes sur la base juridique |
| `data:statistical-analysis` | Analyse statistique des arrêts par matière |
| `data:data-visualization` | Visualiser la couverture de la base juridique |
| `data:create-viz` | Créer des graphiques pour le dashboard |
| `data:build-dashboard` | Dashboard métriques App Droit |
| `data:data-context-extractor` | Extraire le contexte des documents juridiques |
| `csv-data-summarizer` | Résumer les exports CSV de Juridat |
| `postgres` | Requêtes PostgreSQL/pgvector |
| `postgresql-optimization` | Optimiser les requêtes vectorielles |
| `sql-optimization` | Optimiser les requêtes SQL |

### PLUGIN 6 : BRAND-VOICE
Intervient sur : identité de marque, ton, guidelines
Tous les sous-skills :

| Skill | Rôle spécifique dans App Droit |
|---|---|
| `brand-voice:discover-brand` | Découvrir et définir la voix App Droit |
| `brand-voice:generate-guidelines` | Générer les guidelines de marque |
| `brand-voice:guideline-generation` | Documenter le guide de style |
| `brand-voice:brand-voice-enforcement` | Vérifier que tout le contenu respecte la voix |
| `brand-voice:enforce-voice` | Appliquer la voix sur chaque contenu |

### PLUGIN 7 : ENTERPRISE-SEARCH
Intervient sur : recherche d'information, synthèse, veille
Tous les sous-skills :

| Skill | Rôle spécifique dans App Droit |
|---|---|
| `enterprise-search:search` | Rechercher dans les sources juridiques |
| `enterprise-search:search-strategy` | Définir la stratégie de recherche documentaire |
| `enterprise-search:source-management` | Gérer les sources (Juridat, EUR-Lex, HUDOC) |
| `enterprise-search:knowledge-synthesis` | Synthétiser les connaissances juridiques |
| `enterprise-search:digest` | Créer des digests de jurisprudence |

### PLUGIN 8 : BRANCHES DU DROIT BELGE
Intervient sur : toute question juridique specifique a une branche du droit belge.
Chaque skill contient : sources ChromaDB, legislation de reference, strategie RAG, regles d'or.

| Skill | Branche du droit |
|---|---|
| `droit-travail` | Contrats, licenciements, CCT, bien-etre au travail |
| `droit-familial` | Divorce, filiation, autorite parentale, obligations alimentaires |
| `droit-fiscal` | IPP, ISOC, TVA, droits d'enregistrement, succession |
| `droit-penal` | Infractions, peines, procedure penale, detention |
| `droit-civil` | Obligations, contrats, responsabilite, biens, successions |
| `droit-administratif` | Actes administratifs, Conseil d'Etat, fonction publique |
| `droit-commercial` | CSA, insolvabilite, concurrence, FSMA, droit bancaire |
| `droit-immobilier` | Bail, copropriete, vente immobiliere, urbanisme |
| `droit-environnement` | Permis, pollution, dechets, eau, sol, climat, Natura 2000 |
| `droit-propriete-intellectuelle` | Marques, brevets, droits d'auteur, BOIP |
| `droit-securite-sociale` | Chomage, INAMI, pensions, allocations familiales |
| `droit-etrangers` | Sejour, asile, regroupement familial, nationalite |
| `droit-fondamentaux` | Constitution, CEDH, Charte UE, RGPD, discrimination |
| `droit-marches-publics` | Passation, execution, recours, concessions |
| `droit-europeen` | Traites UE, marche interieur, directives, CJUE |

**Regle d'invocation** : Quand une question juridique est posee, identifier la branche et invoquer le skill correspondant AVANT de repondre. Si la question touche plusieurs branches, invoquer tous les skills concernes.

### PLUGIN 9 : HUMANIZER
Intervient sur : toute reponse longue ou destinee a un utilisateur final.

| Skill | Role |
|---|---|
| `humanizer` | Supprimer les patterns d'ecriture IA, ajouter de la personnalite |

**Regle d'invocation** : Appliquer le humanizer sur toute reponse de plus de 3 paragraphes, sur tout contenu marketing, et sur les reponses aux utilisateurs non-juristes. Le humanizer ne modifie jamais les references juridiques ou les citations — il ne touche qu'au ton et au style.

---

## MAPPING COMPLET PAR PHASE

### PHASE 1 — Données juridiques réelles (aucun chiffre inventé)

**Ordre d'exécution obligatoire :**
1. `ralph` → garantir que le scraping tourne jusqu'au bout
2. `gsd-2-agent-framework` → coordonner les agents de scraping
3. `apify-ultimate-scraper` → scraper Juridat.be, EUR-Lex, HUDOC
4. `apify-actor-development` → créer des actors custom si besoin
5. `apify-actorization` → automatiser les pipelines
6. `apify-generate-output-schema` → structurer les données scrapées
7. `web-scraping` → scraping complémentaire
8. `scrapy-web-scraping` → scraping Python Scrapy
9. `enterprise-search:source-management` → gérer les sources
10. `enterprise-search:search-strategy` → stratégie d'indexation
11. `data:validate-data` → valider qualité des données
12. `data:analyze` → analyser la couverture par branche
13. `data:statistical-analysis` → stats sur les données
14. `data:data-visualization` → visualiser la couverture
15. `anthropic-skills:citations-juridiques` → vérifier et formater les citations
16. `anthropic-skills:structure-juridique` → structurer les documents selon normes belges
17. `anthropic-skills:sources-bibliographie` → gérer les sources bibliographiques
18. `legal:compliance-check` → vérifier conformité légale des données
19. `legal:legal-risk-assessment` → évaluer les risques juridiques
20. `doublecheck` → vérifier avant d'indexer
21. `deep-research` → compléter avec recherche vérifiée
22. `enterprise-search:knowledge-synthesis` → synthétiser

### PHASE 2 — Architecture RAG et Backend

**Ordre d'exécution obligatoire :**
1. `ralph` → garantir la complétion
2. `superpowers:write-plan` → planifier l'architecture
3. `superpowers:brainstorm` → brainstormer les choix techniques
4. `engineering:architecture` → concevoir l'architecture RAG
5. `engineering:system-design` → design système complet
6. `software-architecture` → architecture logicielle détaillée
7. `vector-databases` → configurer Qdrant/pgvector
8. `supabase-postgres-best-practices` → base de données
9. `postgres` → modèle de données
10. `postgresql-optimization` → optimisation vectorielle
11. `fastapi-python` → API REST
12. `fastapi-async-patterns` → patterns async
13. `prompt-engineering-patterns` → prompts Claude optimisés
14. `engineering:testing-strategy` → stratégie de tests
15. `superpowers:test-driven-development` → TDD
16. `security-guidance` → sécurité globale
17. `security-best-practices` → bonnes pratiques sécurité
18. `engineering:documentation` → documenter l'API
19. `anthropic-skills:citations-juridiques` → formats de citation corrects dans l'API
20. `legal:review-contract` → review des contrats CGU/CGV de l'app
21. `legal:triage-nda` → NDA pour les partenaires barreaux
22. `gsd-2-agent-framework` → vérifier tous les outputs
23. `droit-*` → configurer les 15 skills de branche (sources, keywords, legislation)
24. `humanizer` → integrer dans le pipeline de reponse
25. `doublecheck` → validation finale

### PHASE 3 — Application Mobile

**Ordre d'exécution obligatoire :**
1. `ralph` → garantir la complétion
2. `superpowers:write-plan` → plan de développement
3. `design:user-research` → recherche utilisateurs avocats
4. `design:research-synthesis` → synthèse des besoins
5. `stitch-design-taste` → DESIGN.md premium
6. `design:design-system` → design system complet
7. `frontend-design:frontend-design` → architecture frontend
8. `stitch-ui-design` → génération screens
9. `stitch-loop` → itération design
10. `ui-ux-pro-max` → standards premium
11. `premium-frontend-ui` → qualité frontend
12. `penpot-uiux-design` → maquettes détaillées
13. `design:ux-copy` → textes UI
14. `design:accessibility-review` → accessibilité WCAG
15. `expo-api-routes` → backend Expo
16. `expo-dev-client` → client de développement
17. `expo-tailwind-setup` → styling
18. `react-native` → composants React Native
19. `native-data-fetching` → fetching données
20. `building-native-ui` → UI native
21. `stripe-integration` → paiements
22. `engineering:code-review` → review code
23. `superpowers:requesting-code-review` → demander review
24. `superpowers:verification-before-completion` → vérifier
25. `expo-cicd-workflows` → CI/CD
26. `expo-deployment` → déploiement stores
27. `engineering:deploy-checklist` → checklist déploiement
28. `design:design-handoff` → handoff développement
29. `gsd-2-agent-framework` → vérification finale
30. `doublecheck` → validation

### PHASE 4 — Validation et Qualité

**Ordre d'exécution obligatoire :**
1. `ralph` → boucle jusqu'à validation complète
2. `superpowers:test-driven-development` → tests
3. `qa` → qualité globale
4. `webapp-testing` → tests web
5. `engineering:testing-strategy` → stratégie tests
6. `superpowers:systematic-debugging` → debugging
7. `engineering:debug` → debug ciblé
8. `root-cause-tracing` → tracer la cause racine
9. `superpowers:requesting-code-review` → review
10. `engineering:code-review` → code review
11. `superpowers:receiving-code-review` → appliquer feedbacks
12. `security-guidance` → audit sécurité
13. `engineering:tech-debt` → dette technique
14. `superpowers:finishing-a-development-branch` → finaliser
15. `superpowers:verification-before-completion` → vérification
16. `doublecheck` → double vérification
17. `gsd-2-agent-framework` → validation finale

### PHASE 5 — Lancement et Croissance

**Ordre d'exécution obligatoire :**

**5A — Identité et Marque :**
1. `brand-voice:discover-brand` → découvrir la voix
2. `brand-voice:generate-guidelines` → guidelines marque
3. `brand-voice:guideline-generation` → documenter
4. `brand-voice:enforce-voice` → appliquer la voix
5. `brand-voice:brand-voice-enforcement` → vérifier cohérence

**5B — Modèle économique (données réelles uniquement) :**
6. `deep-research` → rechercher données marché réelles
7. `gsd-2-agent-framework` → vérifier chaque chiffre
8. `market-sizing-analysis` → TAM/SAM/SOM vérifiés
9. `startup-financial-modeling` → modèle financier
10. `startup-metrics-framework` → métriques clés
11. `pricing-strategy` → stratégie de prix
12. `monetization` → modèle de monétisation

**5C — Go-to-Market :**
13. `gtm-0-to-1-launch` → 10 premiers clients
14. `gtm-positioning-strategy` → positionnement
15. `gtm-product-led-growth` → PLG
16. `gtm-technical-product-pricing` → pricing technique
17. `gtm-partnership-architecture` → partenariats barreaux
18. `gtm-enterprise-account-planning` → grands cabinets
19. `gtm-operating-cadence` → cadence opérationnelle
20. `gtm-board-and-investor-communication` → investisseurs
21. `launch-strategy` → stratégie lancement
22. `product-launch-strategy` → lancement produit
23. `micro-saas-launcher` → lancement SaaS

**5D — Marketing (TOUS les skills marketing) :**
24. `marketing:campaign-plan` → plan campagnes
25. `marketing:content-creation` → contenu
26. `marketing:draft-content` → rédaction
27. `marketing:email-sequence` → emails
28. `marketing:seo-audit` → SEO
29. `marketing:performance-report` → analytics
30. `marketing:competitive-brief` → concurrents
31. `marketing:brand-review` → review marque
32. `content-strategy` → stratégie contenu
33. `content-creator` → créer contenu
34. `content-marketer` → distribuer
35. `seo-audit` → audit SEO complet
36. `programmatic-seo` → SEO programmatique
37. `cold-email` → outreach avocats
38. `lead-magnets` → aimants prospects
39. `lead-research-assistant` → recherche prospects
40. `social-content` → contenu social
41. `linkedin-automation` → LinkedIn
42. `paid-ads` → publicité
43. `growth-engine` → moteur croissance
44. `viral-strategy-engine` → viralité
45. `viral-hook-creator` → hooks
46. `referral-program` → programme référence

---

## RÈGLES PERMANENTES RALPH ET GSD

### Ralph — Actif sur CHAQUE tâche
```
Invoquer ralph au début de CHAQUE tâche.
Ralph garantit que la tâche boucle jusqu'à succès complet.
La tâche ne s'arrête jamais à 80% — seulement à 100% vérifié.
Mot-clé : "ralph", "don't stop", "keep going", "must complete"
```

### GSD — Actif sur CHAQUE vérification
```
gsd-2-agent-framework est le chef d'orchestre de vérification.
Toute donnée venant d'un agent → GSD vérifie avant utilisation.
Toute phase terminée → GSD valide avant de passer à la suivante.
```

---

## MISE À JOUR HEBDOMADAIRE — Chaque lundi matin

Ce skill se met à jour chaque lundi matin :
1. Mettre à jour `last_updated` dans le frontmatter
2. Mettre à jour `next_update` (lundi suivant)
3. Vérifier si de nouveaux skills ont été installés → les ajouter
4. Vérifier si des règles de la Charte ont évolué → les mettre à jour
5. Mettre à jour MEMORY.md avec la nouvelle version

---

## CE QUE CE SKILL NE FAIT JAMAIS
- N'invente aucune donnée
- Ne répond pas "de tête" sans vérification
- Ne saute aucun skill même sous pression de temps
- Ne déclare pas une tâche terminée sans ralph + doublecheck + gsd
- Ne passe pas à la phase suivante sans valider la phase actuelle
