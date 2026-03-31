"""Tests — Lexavo Newsletter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from api.features.newsletter import (
    generate_weekly_newsletter,
    generate_newsletter_html,
    WEEKLY_TIPS,
    WEEKLY_QUESTIONS,
)


def test_generate_newsletter_returns_dict():
    """generate_weekly_newsletter doit retourner un dict."""
    result = generate_weekly_newsletter(week_num=1, domains=["travail"])
    assert isinstance(result, dict), "Le résultat doit être un dict"


def test_newsletter_has_required_fields():
    """Le dict retourné doit contenir tous les champs obligatoires."""
    result = generate_weekly_newsletter(week_num=5, domains=[])
    required = {"subject", "preheader", "hero_title", "weekly_tip", "question", "alerts", "html_content", "text_content", "week_num"}
    for field in required:
        assert field in result, f"Champ manquant : {field}"
    assert result["week_num"] == 5
    assert "Lexavo" in result["subject"]
    assert len(result["weekly_tip"]) > 10


def test_tips_list_not_empty():
    """WEEKLY_TIPS doit contenir exactement 52 éléments non vides."""
    assert len(WEEKLY_TIPS) == 52, f"52 tips attendus, {len(WEEKLY_TIPS)} trouvés"
    for i, tip in enumerate(WEEKLY_TIPS):
        assert isinstance(tip, str), f"Tip {i+1} n'est pas une chaîne"
        assert len(tip) > 5, f"Tip {i+1} est trop court : {tip!r}"


def test_questions_list_not_empty():
    """WEEKLY_QUESTIONS doit contenir au moins 5 questions avec les bons champs."""
    assert len(WEEKLY_QUESTIONS) >= 5, f"Au moins 5 questions attendues, {len(WEEKLY_QUESTIONS)} trouvées"
    for i, q in enumerate(WEEKLY_QUESTIONS):
        assert "title" in q, f"Question {i+1} sans champ 'title'"
        assert "answer" in q, f"Question {i+1} sans champ 'answer'"
        assert "legal_ref" in q, f"Question {i+1} sans champ 'legal_ref'"
        assert len(q["answer"]) >= 30, f"Réponse {i+1} trop courte"


def test_html_contains_lexavo():
    """Le HTML généré doit contenir la marque Lexavo et la structure de base."""
    html = generate_newsletter_html(week_num=1, domains=[])
    assert "Lexavo" in html, "Le HTML doit contenir 'Lexavo'"
    assert "lexavo.be" in html, "Le HTML doit contenir le lien lexavo.be"
    assert "<!DOCTYPE html>" in html, "Le HTML doit être un document HTML complet"
    assert "newsletter_weekly" not in html, "Les tags Jinja2 ne doivent pas apparaître dans le rendu"
