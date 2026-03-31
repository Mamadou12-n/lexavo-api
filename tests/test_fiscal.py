import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.features.fiscal import ask_fiscal

def test_ask_fiscal_mock():
    result = ask_fiscal("Quels sont les frais deductibles pour un independant en Belgique ?", mock=True)
    assert "answer" in result
    assert len(result["answer"]) > 10
    assert "legal_references" in result
    assert "disclaimer" in result

def test_short_question():
    with pytest.raises(ValueError, match="trop courte"):
        ask_fiscal("TVA ?", mock=True)

def test_has_references():
    result = ask_fiscal("Comment fonctionne la deduction des frais professionnels ?", mock=True)
    assert isinstance(result["legal_references"], list)
    assert len(result["legal_references"]) > 0
