import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.features.proof import create_case, add_entry, get_case_summary

def test_create_case():
    case = create_case(user_id=1, title="Harcelement voisin", category="voisinage")
    assert "case_id" in case
    assert case["status"] == "open"
    assert case["entries"] == []

def test_add_entry():
    case = create_case(1, "Test case")
    entry = add_entry(case, "fait", "Le voisin fait du bruit apres 22h")
    assert entry["entry_id"] == 1
    assert "timestamp" in entry
    assert len(case["entries"]) == 1

def test_multiple_entries():
    case = create_case(1, "Test")
    add_entry(case, "fait", "Premier fait documente")
    add_entry(case, "preuve", "Photo prise le 15 mars 2026")
    add_entry(case, "temoin", "Mme Dupont temoin des faits")
    assert len(case["entries"]) == 3

def test_case_summary():
    case = create_case(1, "Dossier test")
    add_entry(case, "fait", "Fait numero un")
    add_entry(case, "fait", "Fait numero deux")
    add_entry(case, "preuve", "Preuve photo")
    summary = get_case_summary(case)
    assert summary["total_entries"] == 3
    assert summary["types_count"]["fait"] == 2

def test_short_title():
    with pytest.raises(ValueError, match="Titre"):
        create_case(1, "ab")

def test_short_content():
    case = create_case(1, "Test")
    with pytest.raises(ValueError, match="Contenu"):
        add_entry(case, "fait", "ab")
