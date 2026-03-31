"""
Tests pour Lexavo Audience Analysis.
"""

import sys
import os
from pathlib import Path

# Make sure scripts/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
from audience_analysis import (
    mock_live_apify_data,
    generate_report,
    generate_html_report,
    LEXAVO_FEATURES,
    FEATURE_DEMAND_SCORES,
)


# ---------------------------------------------------------------------------
# Test 1 — Le mode mock retourne un rapport complet
# ---------------------------------------------------------------------------

def test_mock_analysis_returns_report():
    """Le pipeline mock doit produire un rapport avec tous les champs requis."""
    data = mock_live_apify_data()
    report = generate_report(data)

    assert isinstance(report, dict), "generate_report doit retourner un dict"
    assert "analysis_date" in report
    assert "total_queries_analyzed" in report
    assert "top_10_keywords" in report
    assert "feature_demand_scores" in report
    assert "quick_wins" in report
    assert "content_gaps" in report
    assert "recommended_features_priority" in report

    assert report["total_queries_analyzed"] > 0, "Au moins une requete analysee"
    assert len(report["top_10_keywords"]) == 10, "Exactement 10 keywords"
    assert len(report["recommended_features_priority"]) >= 3, "Au moins 3 features prioritaires"


# ---------------------------------------------------------------------------
# Test 2 — Toutes les features sont presentes dans le rapport
# ---------------------------------------------------------------------------

def test_feature_scores_all_present():
    """Chaque feature Lexavo doit avoir un score dans le rapport."""
    data = mock_live_apify_data()
    report = generate_report(data)
    scores = report["feature_demand_scores"]

    expected_features = set(LEXAVO_FEATURES.keys())
    present_features = set(scores.keys())

    assert expected_features == present_features, (
        f"Features manquantes: {expected_features - present_features}"
    )

    for feat, data in scores.items():
        assert "score" in data, f"{feat} manque 'score'"
        assert "top_query" in data, f"{feat} manque 'top_query'"
        assert "monthly_searches" in data, f"{feat} manque 'monthly_searches'"
        assert 0 <= data["score"] <= 10, f"{feat} score hors [0,10]: {data['score']}"
        assert data["monthly_searches"] >= 0, f"{feat} monthly_searches negatif"


# ---------------------------------------------------------------------------
# Test 3 — Les quick wins ne sont pas vides
# ---------------------------------------------------------------------------

def test_quick_wins_not_empty():
    """Le rapport doit contenir au moins 3 quick wins actionnables."""
    data = mock_live_apify_data()
    report = generate_report(data)

    quick_wins = report["quick_wins"]
    assert len(quick_wins) >= 3, "Au moins 3 quick wins attendus"

    for qw in quick_wins:
        assert "opportunity" in qw, "Quick win sans 'opportunity'"
        assert "monthly_volume" in qw, "Quick win sans 'monthly_volume'"
        assert "difficulty" in qw, "Quick win sans 'difficulty'"
        assert "roi_estimate" in qw, "Quick win sans 'roi_estimate'"
        assert "implementation" in qw, "Quick win sans 'implementation'"
        assert qw["monthly_volume"] > 0, "Volume doit etre positif"

    # Top 3 features doivent apparaitre dans les quick wins ou les priorites
    assert len(report["content_gaps"]) >= 3, "Au moins 3 content gaps identifies"


# ---------------------------------------------------------------------------
# Test 4 — Le rapport HTML est genere
# ---------------------------------------------------------------------------

def test_html_report_generated(tmp_path):
    """Le rapport HTML doit etre genere et contenir les elements cles."""
    data = mock_live_apify_data()
    report = generate_report(data)
    html = generate_html_report(report)

    # Validation du contenu HTML
    assert isinstance(html, str), "generate_html_report doit retourner une chaine"
    assert len(html) > 1000, "Rapport HTML trop court"
    assert "<!DOCTYPE html>" in html
    assert "Lexavo" in html
    assert "lexavo-match" in html
    assert "lexavo-calculateurs" in html
    assert "Quick Wins" in html or "quick" in html.lower()
    assert "avocat bruxelles" in html.lower() or "avocat" in html.lower()

    # Sauvegarde dans tmp_path et verification
    out_file = tmp_path / "audience_analysis_report.html"
    out_file.write_text(html, encoding="utf-8")
    assert out_file.exists(), "Fichier HTML non cree"
    assert out_file.stat().st_size > 1000, "Fichier HTML trop petit"

    # Verification que les 10 features apparaissent
    for feature in LEXAVO_FEATURES:
        assert feature in html, f"Feature {feature} absente du rapport HTML"
