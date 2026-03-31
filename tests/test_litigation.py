import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.features.litigation import get_stages, start_litigation

def test_get_stages():
    stages = get_stages()
    assert len(stages) == 4
    assert stages[0]["name"] == "rappel_amiable"

def test_start_litigation():
    result = start_litigation(
        creditor_name="Dupont SA", debtor_name="Martin SPRL",
        amount=5000, invoice_number="2026-001", due_date="2026-02-15"
    )
    assert result["amount"] == 5000
    assert result["current_stage"] == "rappel_amiable"
    assert len(result["stages"]) == 4
    assert "current_letter" in result

def test_negative_amount():
    with pytest.raises(ValueError, match="positif"):
        start_litigation("A", "B", -100, "INV-1", "2026-01-01")

def test_empty_creditor():
    with pytest.raises(ValueError, match="creancier"):
        start_litigation("", "B", 100, "INV-1", "2026-01-01")

def test_letter_contains_details():
    result = start_litigation("TestCorp", "Debiteur", 1500, "FAC-2026-042", "2026-03-01")
    assert "FAC-2026-042" in result["current_letter"]
    assert "1500.00" in result["current_letter"]
