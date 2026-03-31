import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.features.diagnostic import get_questions, generate_diagnostic


def test_get_questions_returns_6():
    questions = get_questions()
    assert len(questions) == 6
    assert all("question" in q for q in questions)
    assert all("options" in q for q in questions)


def test_generate_diagnostic_mock():
    answers = [
        {"question_id": 1, "answer": "Travail/Emploi"},
        {"question_id": 2, "answer": "Litige en cours"},
        {"question_id": 3, "answer": "1 a 6 mois"},
        {"question_id": 4, "answer": "Non, jamais"},
        {"question_id": 5, "answer": "5.000 - 25.000 EUR"},
        {"question_id": 6, "answer": "Comprendre mes droits"},
    ]
    result = generate_diagnostic(answers, mock=True)
    assert "title" in result
    assert "applicable_rights" in result
    assert isinstance(result["risks"], list)
    assert isinstance(result["priority_actions"], list)
    assert result["branch_detected"] == "droit_travail"


def test_diagnostic_minimum_answers():
    with pytest.raises(ValueError, match="Minimum 3"):
        generate_diagnostic([{"question_id": 1, "answer": "test"}], mock=True)


def test_diagnostic_detects_branch():
    answers = [
        {"question_id": 1, "answer": "Logement/Bail"},
        {"question_id": 2, "answer": "Prevention/Information"},
        {"question_id": 3, "answer": "Pas encore commence"},
    ]
    result = generate_diagnostic(answers, mock=True)
    assert result["branch_detected"] == "droit_immobilier"
