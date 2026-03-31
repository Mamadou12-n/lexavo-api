import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.features.compliance import get_compliance_questions, generate_compliance_audit


def test_get_questions_returns_15():
    questions = get_compliance_questions()
    assert len(questions) == 15
    assert all("category" in q for q in questions)


def test_full_compliance():
    answers = [{"question_id": i, "answer": "yes"} for i in range(1, 16)]
    result = generate_compliance_audit(answers)
    assert result["compliance_score"] == 100
    assert result["overall_status"] == "conforme"
    assert result["risk_level"] == "faible"


def test_zero_compliance():
    answers = [{"question_id": i, "answer": "no"} for i in range(1, 16)]
    result = generate_compliance_audit(answers)
    assert result["compliance_score"] == 0
    assert result["overall_status"] == "non_conforme"
    assert result["risk_level"] == "eleve"
    assert len(result["non_compliant"]) == 15


def test_partial_compliance():
    answers = [{"question_id": i, "answer": "partial"} for i in range(1, 16)]
    result = generate_compliance_audit(answers)
    assert result["compliance_score"] == 50
    assert result["overall_status"] == "partiellement_conforme"


def test_category_breakdown():
    answers = [{"question_id": i, "answer": "yes"} for i in range(1, 16)]
    result = generate_compliance_audit(answers)
    assert "rgpd" in result["category_breakdown"]
    assert "travail" in result["category_breakdown"]
    assert "fiscal" in result["category_breakdown"]


def test_priority_actions():
    answers = [{"question_id": i, "answer": "no"} for i in range(1, 6)]
    answers += [{"question_id": i, "answer": "yes"} for i in range(6, 16)]
    result = generate_compliance_audit(answers)
    assert len(result["priority_actions"]) <= 5


def test_minimum_answers():
    with pytest.raises(ValueError, match="Minimum 5"):
        generate_compliance_audit([{"question_id": 1, "answer": "yes"}])
