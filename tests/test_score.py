import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.features.score import get_score_questions, calculate_score


def test_get_questions_returns_10():
    questions = get_score_questions()
    assert len(questions) == 10
    assert all("weight" in q for q in questions)
    assert sum(q["weight"] for q in questions) == 100


def test_perfect_score():
    answers = [{"question_id": i, "answer": "yes"} for i in range(1, 11)]
    result = calculate_score(answers)
    assert result["score"] == 100
    assert result["rating"] == "excellent"


def test_zero_score():
    answers = [{"question_id": i, "answer": "no"} for i in range(1, 11)]
    result = calculate_score(answers)
    assert result["score"] == 0
    assert result["rating"] == "critique"


def test_partial_score():
    answers = [{"question_id": i, "answer": "partial"} for i in range(1, 11)]
    result = calculate_score(answers)
    assert result["score"] == 50


def test_na_excluded():
    answers = [
        {"question_id": 1, "answer": "yes"},
        {"question_id": 2, "answer": "na"},
        {"question_id": 3, "answer": "yes"},
        {"question_id": 4, "answer": "yes"},
        {"question_id": 5, "answer": "yes"},
    ]
    result = calculate_score(answers)
    assert result["score"] == 100  # na excluded from calculation


def test_weak_points_identified():
    answers = [
        {"question_id": 1, "answer": "no"},
        {"question_id": 2, "answer": "yes"},
        {"question_id": 3, "answer": "no"},
        {"question_id": 4, "answer": "yes"},
        {"question_id": 5, "answer": "yes"},
    ]
    result = calculate_score(answers)
    assert len(result["weak_points"]) == 2
    assert any("contrat de travail" in wp["question"] for wp in result["weak_points"])


def test_category_breakdown():
    answers = [{"question_id": i, "answer": "yes"} for i in range(1, 11)]
    result = calculate_score(answers)
    assert "category_breakdown" in result
    assert "travail" in result["category_breakdown"]


def test_minimum_answers():
    with pytest.raises(ValueError, match="Minimum 5"):
        calculate_score([{"question_id": 1, "answer": "yes"}])
