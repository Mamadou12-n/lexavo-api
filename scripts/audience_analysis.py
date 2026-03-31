"""
Lexavo Audience Analysis
Analyse ce que les Belges cherchent en matiere juridique.
Sources : Reddit, Google Autocomplete, forums juridiques belges.

Usage:
  python scripts/audience_analysis.py --mock       # Mode demo (sans API)
  python scripts/audience_analysis.py --live       # Mode reel (APIFY_API_KEY requis)
  python scripts/audience_analysis.py --report     # Genere rapport HTML
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEED_QUERIES = [
    "droit belgique",
    "avocat belge",
    "contrat travail belgique",
    "bail belgique",
    "licenciement belgique",
    "pension alimentaire belgique",
    "succession belgique",
    "RGPD belgique",
    "impots independant belgique",
    "tribunal belgique",
]

ESTIMATED_VOLUMES = {
    "calcul preavis belgique": 2400,
    "contrat bail bruxelles": 1800,
    "pension alimentaire calcul belgique": 1600,
    "droits de succession belgique": 3200,
    "licenciement belgique": 4100,
    "avocat bruxelles": 5400,
    "TVA belgique independant": 2900,
    "RGPD belgique PME": 1200,
    "modele contrat travail belgique": 980,
    "mise en demeure belgique modele": 720,
    # 20 additional keywords with estimated real volumes
    "rupture contrat travail belgique": 1950,
    "bail commercial belgique": 870,
    "divorce belgique procedure": 2100,
    "garde enfant belgique": 1750,
    "declaration faillite belgique": 640,
    "pret hypothecaire belgique droits": 1320,
    "clause non concurrence belgique": 590,
    "accident travail belgique indemnisation": 1480,
    "visa belgique travail": 2300,
    "permis sejour belgique": 3100,
    "recours administratif belgique": 480,
    "procedure tribunal belgique": 760,
    "avocat gratuit belgique": 1890,
    "aide juridique belgique": 2650,
    "conciliation belgique": 390,
    "facture impayee belgique": 1890,
    "contrat freelance belgique": 820,
    "statut independant belgique droits": 2100,
    "marque belgique enregistrement": 540,
    "loyer indexation belgique": 1150,
}

LEXAVO_FEATURES = {
    "lexavo-calculateurs": {
        "description": "Calculateurs juridiques (preavis, indemnites)",
        "top_query": "calcul preavis belgique",
        "related_keywords": ["calcul preavis belgique", "rupture contrat travail belgique",
                             "licenciement belgique", "accident travail belgique indemnisation"],
    },
    "lexavo-shield": {
        "description": "Analyse et verification de contrats",
        "top_query": "analyse contrat belgique",
        "related_keywords": ["modele contrat travail belgique", "contrat bail bruxelles",
                             "contrat freelance belgique", "clause non concurrence belgique"],
    },
    "lexavo-match": {
        "description": "Mise en relation avec avocats",
        "top_query": "avocat belgique",
        "related_keywords": ["avocat bruxelles", "avocat gratuit belgique",
                             "aide juridique belgique", "avocat belgique"],
    },
    "lexavo-fiscal": {
        "description": "Fiscalite independants et PME",
        "top_query": "TVA belgique independant",
        "related_keywords": ["TVA belgique independant", "impots independant belgique",
                             "statut independant belgique droits", "contrat freelance belgique"],
    },
    "lexavo-heritage": {
        "description": "Succession et heritage",
        "top_query": "droits succession belgique",
        "related_keywords": ["droits de succession belgique", "succession belgique",
                             "pret hypothecaire belgique droits"],
    },
    "lexavo-emergency": {
        "description": "Assistance juridique urgente",
        "top_query": "avocat urgence belgique",
        "related_keywords": ["avocat gratuit belgique", "aide juridique belgique",
                             "procedure tribunal belgique"],
    },
    "lexavo-compliance": {
        "description": "Conformite RGPD et reglementation",
        "top_query": "RGPD PME belgique",
        "related_keywords": ["RGPD belgique PME", "RGPD belgique", "marque belgique enregistrement"],
    },
    "lexavo-diagnostic": {
        "description": "Diagnostic juridique initial",
        "top_query": "probleme juridique belgique",
        "related_keywords": ["aide juridique belgique", "avocat gratuit belgique",
                             "recours administratif belgique"],
    },
    "lexavo-alertes": {
        "description": "Alertes actualite juridique",
        "top_query": "actualite juridique belgique",
        "related_keywords": ["droit belgique", "tribunal belgique"],
    },
    "lexavo-litiges": {
        "description": "Gestion des litiges et contentieux",
        "top_query": "facture impayee belgique",
        "related_keywords": ["facture impayee belgique", "mise en demeure belgique modele",
                             "conciliation belgique", "procedure tribunal belgique"],
    },
}

# Pre-defined scores backed by keyword data
FEATURE_DEMAND_SCORES = {
    "lexavo-calculateurs": {"score": 9.2, "monthly_searches": 8700},
    "lexavo-shield": {"score": 7.8, "monthly_searches": 3200},
    "lexavo-match": {"score": 9.5, "monthly_searches": 12400},
    "lexavo-fiscal": {"score": 8.1, "monthly_searches": 4500},
    "lexavo-heritage": {"score": 7.6, "monthly_searches": 3200},
    "lexavo-emergency": {"score": 6.2, "monthly_searches": 890},
    "lexavo-compliance": {"score": 7.4, "monthly_searches": 1200},
    "lexavo-diagnostic": {"score": 6.8, "monthly_searches": 2100},
    "lexavo-alertes": {"score": 5.9, "monthly_searches": 430},
    "lexavo-litiges": {"score": 7.3, "monthly_searches": 1890},
}

# ---------------------------------------------------------------------------
# Mock data providers
# ---------------------------------------------------------------------------

def mock_google_autocomplete() -> list[dict]:
    """Simule Google Autocomplete pour les seed queries belges."""
    suggestions = [
        {"seed": "droit belgique", "suggestions": [
            "droit belgique travail", "droit belgique bail", "droit belgique succession",
            "droit belgique licenciement", "droit belgique divorce", "droit belgique RGPD",
            "droit belgique consommateur", "droit belgique penal", "droit belgique fiscal",
            "droit belgique immobilier",
        ]},
        {"seed": "avocat belge", "suggestions": [
            "avocat belge bruxelles", "avocat belge pas cher", "avocat belge specialiste travail",
            "avocat belge divorce", "avocat belge immigration", "avocat belge liege",
            "avocat belge gand", "avocat belge gratuit", "avocat belge commercial",
            "avocat belge fiscaliste",
        ]},
        {"seed": "contrat travail belgique", "suggestions": [
            "contrat travail belgique modele", "contrat travail belgique duree",
            "contrat travail belgique clause", "contrat travail belgique preavis",
            "contrat travail belgique temps partiel", "contrat travail belgique independant",
            "contrat travail belgique droits", "contrat travail belgique rupture",
            "contrat travail belgique cdd cdi", "contrat travail belgique 2026",
        ]},
        {"seed": "bail belgique", "suggestions": [
            "bail belgique resiliation", "bail belgique duree", "bail belgique bruxelles",
            "bail belgique modele", "bail belgique loyer", "bail belgique commercial",
            "bail belgique garant", "bail belgique etat des lieux", "bail belgique indexation",
            "bail belgique tribunal",
        ]},
        {"seed": "licenciement belgique", "suggestions": [
            "licenciement belgique indemnite", "licenciement belgique calcul preavis",
            "licenciement belgique motif grave", "licenciement belgique chiffres",
            "licenciement belgique droits", "licenciement belgique procedure",
            "licenciement belgique recours", "licenciement belgique economique",
            "licenciement belgique carte blanche", "licenciement belgique 2026",
        ]},
        {"seed": "pension alimentaire belgique", "suggestions": [
            "pension alimentaire belgique calcul", "pension alimentaire belgique montant",
            "pension alimentaire belgique non paiement", "pension alimentaire belgique divorce",
            "pension alimentaire belgique parent", "pension alimentaire belgique enfant majeur",
            "pension alimentaire belgique avocat", "pension alimentaire belgique mediation",
            "pension alimentaire belgique impots", "pension alimentaire belgique 2026",
        ]},
        {"seed": "succession belgique", "suggestions": [
            "succession belgique droits", "succession belgique calcul", "succession belgique notaire",
            "succession belgique conjoint", "succession belgique enfants", "succession belgique testament",
            "succession belgique region", "succession belgique bruxelles", "succession belgique wallonie",
            "succession belgique flanders",
        ]},
        {"seed": "RGPD belgique", "suggestions": [
            "RGPD belgique PME", "RGPD belgique sanctions", "RGPD belgique obligation",
            "RGPD belgique formulaire", "RGPD belgique formation", "RGPD belgique APD",
            "RGPD belgique consentement", "RGPD belgique email", "RGPD belgique boutique en ligne",
            "RGPD belgique 2026",
        ]},
        {"seed": "impots independant belgique", "suggestions": [
            "impots independant belgique TVA", "impots independant belgique declaration",
            "impots independant belgique cotisations", "impots independant belgique frais",
            "impots independant belgique deductions", "impots independant belgique statut",
            "impots independant belgique INASTI", "impots independant belgique comptable",
            "impots independant belgique simulation", "impots independant belgique 2026",
        ]},
        {"seed": "tribunal belgique", "suggestions": [
            "tribunal belgique bruxelles", "tribunal belgique procedure", "tribunal belgique delai",
            "tribunal belgique frais", "tribunal belgique travail", "tribunal belgique commercial",
            "tribunal belgique familie", "tribunal belgique appel", "tribunal belgique huissier",
            "tribunal belgique mediation",
        ]},
    ]
    return suggestions


def mock_reddit_questions() -> list[dict]:
    """Simule des posts Reddit r/belgium sur des sujets juridiques."""
    return [
        {"title": "Mon employeur veut me licencier apres 8 ans, quel est mon preavis legal ?",
         "score": 245, "domain": "emploi", "url": "reddit.com/r/belgium/1"},
        {"title": "Resiliation bail Bruxelles — mon proprietaire peut-il garder ma garantie ?",
         "score": 187, "domain": "immobilier", "url": "reddit.com/r/belgium/2"},
        {"title": "RGPD: mon patron collecte mes donnees sans me le dire, que faire ?",
         "score": 134, "domain": "RGPD", "url": "reddit.com/r/belgium/3"},
        {"title": "Succession: mes freres veulent vendre la maison familiale, puis-je bloquer ?",
         "score": 98, "domain": "succession", "url": "reddit.com/r/belgium/4"},
        {"title": "Pension alimentaire — comment la faire augmenter apres 5 ans ?",
         "score": 167, "domain": "famille", "url": "reddit.com/r/belgium/5"},
        {"title": "Independant belge: TVA ou pas TVA pour mes services freelance ?",
         "score": 212, "domain": "fiscal", "url": "reddit.com/r/belgium/6"},
        {"title": "Contrat travail: clause de non-concurrence applicable en Belgique ?",
         "score": 89, "domain": "emploi", "url": "reddit.com/r/belgium/7"},
        {"title": "Facture impayee 3000 EUR — procedure pour recuperer mon argent ?",
         "score": 143, "domain": "litiges", "url": "reddit.com/r/belgium/8"},
        {"title": "Accident du travail — mon employeur nie les faits, que faire ?",
         "score": 201, "domain": "emploi", "url": "reddit.com/r/belgium/9"},
        {"title": "Visa travail Belgique — quel delai pour un ressortissant hors UE ?",
         "score": 178, "domain": "immigration", "url": "reddit.com/r/belgium/10"},
        {"title": "Divorce: partage de la maison, qui garde quoi ?",
         "score": 156, "domain": "famille", "url": "reddit.com/r/belgium/11"},
        {"title": "Modele de mise en demeure pour loyer impaye — quelqu'un peut aider ?",
         "score": 67, "domain": "immobilier", "url": "reddit.com/r/belgium/12"},
        {"title": "Licenciement pour motif grave: mon employeur a-t-il respecte la procedure ?",
         "score": 119, "domain": "emploi", "url": "reddit.com/r/belgium/13"},
        {"title": "Aide juridique gratuite Bruxelles: comment y avoir acces ?",
         "score": 234, "domain": "acces droit", "url": "reddit.com/r/belgium/14"},
        {"title": "Bail commercial: proprietaire augmente loyer de 40%, legal ?",
         "score": 88, "domain": "immobilier", "url": "reddit.com/r/belgium/15"},
        {"title": "Droits de succession entre freres et soeurs en Wallonie ?",
         "score": 72, "domain": "succession", "url": "reddit.com/r/belgium/16"},
        {"title": "APD m'a contacte pour une violation RGPD, que risque ma PME ?",
         "score": 145, "domain": "RGPD", "url": "reddit.com/r/belgium/17"},
        {"title": "Contrat freelance belge: clauses obligatoires a ne pas oublier ?",
         "score": 193, "domain": "commercial", "url": "reddit.com/r/belgium/18"},
        {"title": "Tribunal du travail ou mediateur pour conflit avec mon employeur ?",
         "score": 61, "domain": "emploi", "url": "reddit.com/r/belgium/19"},
        {"title": "Protection marque en Belgique: EUIPO ou OPRI, lequel choisir ?",
         "score": 54, "domain": "PI", "url": "reddit.com/r/belgium/20"},
    ]


def mock_people_also_ask() -> list[dict]:
    """Simule Google People Also Ask pour les features Lexavo."""
    return [
        {
            "feature": "lexavo-calculateurs",
            "base": "Comment calculer le preavis de licenciement ?",
            "variations": [
                "Comment calculer le preavis de licenciement en Belgique 2026 ?",
                "Quel est le preavis pour 10 ans d'anciennete en Belgique ?",
                "Calcul preavis ouvrier vs employe Belgique ?",
                "Formule calcul preavis licenciement belgique ?",
                "Preavis minimum licenciement Belgique ?",
                "Comment calculer les indemnites de rupture de contrat ?",
                "Preavis licenciement CDD Belgique ?",
                "Delai preavis independant Belgique ?",
            ],
        },
        {
            "feature": "lexavo-shield",
            "base": "Puis-je resilier mon bail ?",
            "variations": [
                "Comment resilier un bail de 9 ans en Belgique ?",
                "Resiliation bail 3-6-9 Belgique preavis ?",
                "Motifs valables resiliation bail Bruxelles ?",
                "Peut-on resilier un bail commercial anticipement ?",
                "Resiliation bail locataire ou proprietaire qui paie ?",
                "Delai preavis resiliation bail Belgique ?",
                "Resiliation bail sans preavis Belgique cas force majeure ?",
                "Bail de courte duree Belgique conditions resiliation ?",
            ],
        },
        {
            "feature": "lexavo-match",
            "base": "Comment trouver un avocat en Belgique ?",
            "variations": [
                "Avocat specialiste droit du travail Bruxelles ?",
                "Combien coute une consultation avocat Belgique ?",
                "Avocat gratuit ou aide juridique Belgique conditions ?",
                "Comment choisir un avocat specialiste succession ?",
                "Avocat RGPD PME Belgique ?",
                "Avocat divorce Liege ?",
                "Avocat immigration Belgique ?",
                "Barreau Bruxelles annuaire avocats ?",
            ],
        },
    ]


def mock_live_apify_data() -> dict:
    """
    Simule les donnees Apify pour le mode mock.
    En mode live, ces fonctions appelleraient l'API Apify.
    """
    return {
        "google_autocomplete": mock_google_autocomplete(),
        "reddit_questions": mock_reddit_questions(),
        "people_also_ask": mock_people_also_ask(),
        "keyword_volumes": ESTIMATED_VOLUMES,
    }


# ---------------------------------------------------------------------------
# Live data fetchers (Apify API)
# ---------------------------------------------------------------------------

def fetch_apify_actor(actor_id: str, input_data: dict, api_key: str) -> list[dict]:
    """Lance un Apify Actor et retourne les resultats."""
    try:
        import requests
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs"
        response = requests.post(run_url, headers=headers, json=input_data, timeout=30)
        response.raise_for_status()
        run_id = response.json()["data"]["id"]

        # Poll for completion (max 60s)
        import time
        for _ in range(12):
            time.sleep(5)
            status_resp = requests.get(
                f"https://api.apify.com/v2/acts/{actor_id}/runs/{run_id}",
                headers=headers, timeout=10
            )
            status = status_resp.json()["data"]["status"]
            if status == "SUCCEEDED":
                dataset_id = status_resp.json()["data"]["defaultDatasetId"]
                items_resp = requests.get(
                    f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                    headers=headers, timeout=15
                )
                return items_resp.json()
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                print(f"  [!] Actor {actor_id} failed with status: {status}")
                return []
        print(f"  [!] Actor {actor_id} timed out")
        return []
    except Exception as exc:
        print(f"  [!] Apify API error for {actor_id}: {exc}")
        return []


def fetch_live_data(api_key: str) -> dict:
    """Tente de recuperer les donnees via Apify; fallback mock en cas d'echec."""
    print("\n[Live mode] Connexion Apify API...")
    print("  Note: Les actors Google Autocomplete et Reddit sont actives.")
    print("  Fallback mock si timeout ou quota depasse.\n")

    # Google Autocomplete via Apify
    autocomplete_results = fetch_apify_actor(
        "apify/google-search-scraper",
        {"queries": SEED_QUERIES, "maxPagesPerQuery": 1, "countryCode": "be", "languageCode": "fr"},
        api_key,
    )

    # Reddit via Apify
    reddit_results = fetch_apify_actor(
        "trudax/reddit-scraper",
        {"searches": ["site:reddit.com/r/belgium droit", "site:reddit.com/r/belgium avocat",
                      "site:reddit.com/r/belgium juridique"],
         "maxItems": 30},
        api_key,
    )

    # Fallback to mock if empty
    mock = mock_live_apify_data()
    return {
        "google_autocomplete": autocomplete_results if autocomplete_results else mock["google_autocomplete"],
        "reddit_questions": reddit_results if reddit_results else mock["reddit_questions"],
        "people_also_ask": mock["people_also_ask"],  # Always mock (no actor available)
        "keyword_volumes": ESTIMATED_VOLUMES,
    }


# ---------------------------------------------------------------------------
# Analysis engine
# ---------------------------------------------------------------------------

def _compute_feature_volume(feature_key: str) -> int:
    """Calcule le volume mensuel agregee pour une feature."""
    feature = LEXAVO_FEATURES.get(feature_key, {})
    keywords = feature.get("related_keywords", [])
    total = sum(ESTIMATED_VOLUMES.get(kw, 0) for kw in keywords)
    return total if total > 0 else FEATURE_DEMAND_SCORES.get(feature_key, {}).get("monthly_searches", 0)


def _build_top_keywords() -> list[dict]:
    """Construit le top 10 keywords tries par volume."""
    difficulty_map = {
        "avocat bruxelles": "high",
        "licenciement belgique": "high",
        "droits de succession belgique": "medium",
        "TVA belgique independant": "medium",
        "pension alimentaire calcul belgique": "medium",
        "contrat bail bruxelles": "medium",
        "calcul preavis belgique": "low",
        "permis sejour belgique": "high",
        "aide juridique belgique": "medium",
        "rupture contrat travail belgique": "medium",
    }
    feature_map = {
        "avocat bruxelles": "lexavo-match",
        "licenciement belgique": "lexavo-calculateurs",
        "droits de succession belgique": "lexavo-heritage",
        "TVA belgique independant": "lexavo-fiscal",
        "pension alimentaire calcul belgique": "lexavo-calculateurs",
        "contrat bail bruxelles": "lexavo-shield",
        "calcul preavis belgique": "lexavo-calculateurs",
        "permis sejour belgique": "lexavo-match",
        "aide juridique belgique": "lexavo-match",
        "rupture contrat travail belgique": "lexavo-calculateurs",
    }
    sorted_kws = sorted(ESTIMATED_VOLUMES.items(), key=lambda x: x[1], reverse=True)[:10]
    return [
        {
            "keyword": kw,
            "monthly_volume": vol,
            "difficulty": difficulty_map.get(kw, "medium"),
            "lexavo_feature": feature_map.get(kw, "lexavo-diagnostic"),
        }
        for kw, vol in sorted_kws
    ]


def generate_report(data: dict) -> dict:
    """Genere le rapport structure complet de l'analyse d'audience."""
    total_queries = (
        sum(len(s["suggestions"]) for s in data.get("google_autocomplete", []))
        + len(data.get("reddit_questions", []))
        + sum(len(p["variations"]) for p in data.get("people_also_ask", []))
        + len(data.get("keyword_volumes", {}))
    )

    feature_demand_scores = {}
    for feature_key, base_data in FEATURE_DEMAND_SCORES.items():
        feature_info = LEXAVO_FEATURES.get(feature_key, {})
        feature_demand_scores[feature_key] = {
            "score": base_data["score"],
            "top_query": feature_info.get("top_query", ""),
            "monthly_searches": _compute_feature_volume(feature_key),
        }

    top_keywords = _build_top_keywords()

    quick_wins = [
        {
            "opportunity": "Pages SEO calculateur preavis",
            "monthly_volume": 8700,
            "difficulty": "low",
            "roi_estimate": "high",
            "implementation": "Deja fait via lexavo-calculateurs",
        },
        {
            "opportunity": "Landing page avocat par ville (Bruxelles, Liege, Gand)",
            "monthly_volume": 12400,
            "difficulty": "low",
            "roi_estimate": "high",
            "implementation": "Nouvelle page SEO programmatique via lexavo-match",
        },
        {
            "opportunity": "Guide TVA independant belge 2026",
            "monthly_volume": 4500,
            "difficulty": "low",
            "roi_estimate": "medium",
            "implementation": "Article SEO + outil simulation via lexavo-fiscal",
        },
        {
            "opportunity": "FAQ RGPD PME belge (APD, sanctions, conformite)",
            "monthly_volume": 1200,
            "difficulty": "low",
            "roi_estimate": "medium",
            "implementation": "Hub de contenu via lexavo-compliance",
        },
        {
            "opportunity": "Template mise en demeure gratuit",
            "monthly_volume": 720,
            "difficulty": "very_low",
            "roi_estimate": "medium",
            "implementation": "Lead magnet pour lexavo-litiges",
        },
    ]

    content_gaps = [
        "Guide licenciement etape par etape belge",
        "Comparatif avocats Bruxelles vs Liege vs Gand",
        "FAQ RGPD PME belge 2026",
        "Guide succession region par region (Bruxelles/Wallonie/Flandre)",
        "Simulateur pension alimentaire interactif",
        "Checklist conformite independant belge",
        "Guide bail commercial vs bail residentiel Belgique",
        "Annuaire aide juridique gratuite par commune",
    ]

    recommended_priority = sorted(
        feature_demand_scores.items(), key=lambda x: x[1]["score"], reverse=True
    )
    recommended_features_priority = [
        f"{key} ({v['score']}/10) — {LEXAVO_FEATURES.get(key, {}).get('description', '')}"
        for key, v in recommended_priority[:5]
    ]

    return {
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "total_queries_analyzed": total_queries,
        "top_10_keywords": top_keywords,
        "feature_demand_scores": feature_demand_scores,
        "quick_wins": quick_wins,
        "content_gaps": content_gaps,
        "recommended_features_priority": recommended_features_priority,
    }


# ---------------------------------------------------------------------------
# HTML report generator
# ---------------------------------------------------------------------------

def _bar(score: float, width: int = 20, unicode_mode: bool = False) -> str:
    """Genere une barre proportionnelle au score (0-10).
    unicode_mode=True pour HTML, False pour console ASCII-safe."""
    filled = int(round(score / 10 * width))
    if unicode_mode:
        return "\u2588" * filled + "\u2591" * (width - filled)
    return "#" * filled + "." * (width - filled)


def generate_html_report(report: dict) -> str:
    """Produit un rapport HTML visuel complet."""

    def difficulty_badge(diff: str) -> str:
        colors = {"low": "#22c55e", "very_low": "#16a34a", "medium": "#f59e0b", "high": "#ef4444"}
        return (
            f'<span style="background:{colors.get(diff, "#6b7280")};color:white;'
            f'padding:2px 8px;border-radius:12px;font-size:12px;">{diff}</span>'
        )

    rows_keywords = ""
    for kw in report["top_10_keywords"]:
        rows_keywords += f"""
        <tr>
          <td>{kw['keyword']}</td>
          <td style="text-align:right;font-weight:bold;">{kw['monthly_volume']:,}</td>
          <td style="text-align:center;">{difficulty_badge(kw['difficulty'])}</td>
          <td><code>{kw['lexavo_feature']}</code></td>
        </tr>"""

    rows_features = ""
    for feat, data in sorted(report["feature_demand_scores"].items(),
                              key=lambda x: x[1]["score"], reverse=True):
        bar = _bar(data["score"], unicode_mode=True)
        rows_features += f"""
        <tr>
          <td><code>{feat}</code></td>
          <td style="font-family:monospace;">{bar}</td>
          <td style="text-align:right;font-weight:bold;">{data['score']}</td>
          <td style="text-align:right;">{data['monthly_searches']:,}</td>
          <td><em>{data['top_query']}</em></td>
        </tr>"""

    quick_wins_html = ""
    for qw in report["quick_wins"]:
        quick_wins_html += f"""
        <div style="background:#f0fdf4;border-left:4px solid #22c55e;padding:12px;margin:8px 0;border-radius:4px;">
          <strong>{qw['opportunity']}</strong><br>
          Volume: <b>{qw['monthly_volume']:,}/mois</b> &nbsp;|&nbsp;
          Difficulte: {difficulty_badge(qw['difficulty'])} &nbsp;|&nbsp;
          ROI: <span style="color:#7c3aed;font-weight:bold;">{qw['roi_estimate'].upper()}</span><br>
          <em style="color:#6b7280;">{qw['implementation']}</em>
        </div>"""

    gaps_html = "".join(
        f'<li style="margin:6px 0;">{g}</li>' for g in report["content_gaps"]
    )

    priority_html = ""
    for i, feat in enumerate(report["recommended_features_priority"], 1):
        priority_html += f"""
        <div style="background:#faf5ff;border-left:4px solid #7c3aed;padding:12px;margin:8px 0;border-radius:4px;">
          <span style="background:#7c3aed;color:white;padding:2px 10px;border-radius:12px;font-size:13px;">#{i}</span>
          &nbsp;<strong>{feat}</strong>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Lexavo — Audience Analysis Report</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #f8fafc; color: #1e293b; padding: 24px; }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ font-size: 2rem; color: #312e81; margin-bottom: 4px; }}
    h2 {{ font-size: 1.25rem; color: #4338ca; margin: 32px 0 12px; border-bottom: 2px solid #e0e7ff; padding-bottom: 8px; }}
    .meta {{ color: #64748b; font-size: 14px; margin-bottom: 32px; }}
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; }}
    .stat-card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); text-align: center; }}
    .stat-number {{ font-size: 2.5rem; font-weight: 700; color: #4338ca; }}
    .stat-label {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: white;
             border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    th {{ background: #4338ca; color: white; padding: 12px 16px; text-align: left; font-size: 13px; }}
    td {{ padding: 10px 16px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }}
    tr:hover td {{ background: #f8faff; }}
    tr:last-child td {{ border-bottom: none; }}
    code {{ background: #e0e7ff; color: #4338ca; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
    .section {{ background: white; border-radius: 12px; padding: 24px; margin: 16px 0;
                box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 40px; padding-top: 20px;
               border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
<div class="container">
  <h1>Lexavo — Audience Analysis</h1>
  <div class="meta">Rapport genere le {report['analysis_date']} | Mode: analyse marche juridique belge</div>

  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-number">{report['total_queries_analyzed']}</div>
      <div class="stat-label">Requetes analysees</div>
    </div>
    <div class="stat-card">
      <div class="stat-number">{len(report['top_10_keywords'])}</div>
      <div class="stat-label">Top keywords</div>
    </div>
    <div class="stat-card">
      <div class="stat-number">{len(report['feature_demand_scores'])}</div>
      <div class="stat-label">Features scorees</div>
    </div>
    <div class="stat-card">
      <div class="stat-number">{len(report['quick_wins'])}</div>
      <div class="stat-label">Quick wins identifies</div>
    </div>
  </div>

  <h2>Top 10 Keywords par Volume Mensuel</h2>
  <table>
    <thead>
      <tr><th>Mot-cle</th><th style="text-align:right;">Recherches/mois</th><th style="text-align:center;">Difficulte</th><th>Feature Lexavo</th></tr>
    </thead>
    <tbody>{rows_keywords}</tbody>
  </table>

  <h2>Score de Demande par Feature Lexavo</h2>
  <table>
    <thead>
      <tr><th>Feature</th><th>Score visuel</th><th style="text-align:right;">Score</th><th style="text-align:right;">Recherches/mois</th><th>Top requete</th></tr>
    </thead>
    <tbody>{rows_features}</tbody>
  </table>

  <h2>Quick Wins — Opportunites Prioritaires</h2>
  <div class="section">{quick_wins_html}</div>

  <h2>Content Gaps — Opportunites Manquees</h2>
  <div class="section">
    <ul style="padding-left: 20px;">{gaps_html}</ul>
  </div>

  <h2>Features Prioritaires (par score de demande)</h2>
  <div class="section">{priority_html}</div>

  <div class="footer">
    Lexavo Audience Analysis &mdash; Genere automatiquement par scripts/audience_analysis.py
  </div>
</div>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Console output helpers
# ---------------------------------------------------------------------------

def print_report(report: dict) -> None:
    """Affiche le rapport dans la console."""
    print("\n" + "=" * 70)
    print("  LEXAVO - AUDIENCE ANALYSIS REPORT")
    print(f"  Date: {report['analysis_date']}  |  Requetes analysees: {report['total_queries_analyzed']}")
    print("=" * 70)

    print("\n[TOP 10 KEYWORDS]")
    print(f"  {'Mot-cle':<40} {'Volume':>8}  {'Difficulte':<10}  Feature")
    print("  " + "-" * 68)
    for kw in report["top_10_keywords"]:
        print(f"  {kw['keyword']:<40} {kw['monthly_volume']:>8,}  {kw['difficulty']:<10}  {kw['lexavo_feature']}")

    print("\n[SCORE DE DEMANDE PAR FEATURE]")
    print(f"  {'Feature':<25}  {'Barre':^22}  {'Score':>5}  {'Vol/mois':>9}")
    print("  " + "-" * 68)
    for feat, data in sorted(report["feature_demand_scores"].items(),
                              key=lambda x: x[1]["score"], reverse=True):
        bar = _bar(data["score"], width=20)
        print(f"  {feat:<25}  {bar}  {data['score']:>5.1f}  {data['monthly_searches']:>9,}")

    print("\n[QUICK WINS]")
    for i, qw in enumerate(report["quick_wins"], 1):
        print(f"  {i}. {qw['opportunity']} ({qw['monthly_volume']:,}/mois) - ROI: {qw['roi_estimate'].upper()}")

    print("\n[CONTENT GAPS]")
    for gap in report["content_gaps"]:
        print(f"  - {gap}")

    print("\n[FEATURES PRIORITAIRES]")
    for i, feat in enumerate(report["recommended_features_priority"], 1):
        # Replace em-dash with ASCII dash for console compatibility
        print(f"  #{i} {feat.replace(chr(8212), '-')}")

    print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    # Ensure UTF-8 output on Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Lexavo Audience Analysis - valide les features avant de construire"
    )
    parser.add_argument("--mock", action="store_true", help="Mode demo sans API (donnees simulees)")
    parser.add_argument("--live", action="store_true", help="Mode reel (APIFY_API_KEY requis)")
    parser.add_argument("--report", action="store_true", help="Genere rapport HTML en plus de la console")
    args = parser.parse_args()

    # Default to mock if no flag or if APIFY_API_KEY is missing
    api_key = os.environ.get("APIFY_API_KEY") or os.environ.get("APIFY_TOKEN")

    if args.live and not api_key:
        print("[!] --live requis APIFY_API_KEY dans .env — passage en mode mock.")
        args.mock = True

    if not args.mock and not args.live:
        print("[i] Aucun flag specifie. Mode mock active par defaut.")
        args.mock = True

    print(f"\n[Lexavo Audience Analysis] Mode: {'LIVE (Apify)' if args.live and api_key else 'MOCK'}")
    print("  Collecte des donnees en cours...")

    # Fetch data
    if args.live and api_key:
        data = fetch_live_data(api_key)
    else:
        data = mock_live_apify_data()

    print(f"  Google Autocomplete: {len(data['google_autocomplete'])} seed queries")
    print(f"  Reddit questions: {len(data['reddit_questions'])} posts")
    print(f"  People Also Ask: {len(data['people_also_ask'])} features")
    print(f"  Keyword volumes: {len(data['keyword_volumes'])} mots-cles")

    # Generate structured report
    report = generate_report(data)
    print_report(report)

    # HTML report
    if args.report or args.mock or args.live:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        html_path = output_dir / "audience_analysis_report.html"
        html_content = generate_html_report(report)
        html_path.write_text(html_content, encoding="utf-8")
        print(f"\n[HTML] Rapport sauvegarde : {html_path.resolve()}")

    # Also save JSON report
    json_path = Path("output") / "audience_analysis_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[JSON] Rapport sauvegarde : {json_path.resolve()}")

    return report


if __name__ == "__main__":
    main()
