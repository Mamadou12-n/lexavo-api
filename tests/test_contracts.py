import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.features.contracts import list_templates, get_template, generate_contract_html


def test_list_all_templates():
    templates = list_templates()
    assert len(templates) >= 8
    assert all("title" in t for t in templates)
    assert all("price_cents" in t for t in templates)


def test_filter_by_category():
    bail_templates = list_templates(category="bail")
    assert len(bail_templates) == 3  # bruxelles, wallonie, flandre
    assert all(t["category"] == "bail" for t in bail_templates)


def test_filter_by_region():
    bxl = list_templates(region="bruxelles")
    assert all(t.get("region") in ("bruxelles", None) for t in bxl)


def test_get_template_exists():
    template = get_template("bail_bruxelles")
    assert template is not None
    assert template["id"] == "bail_bruxelles"
    assert "variables" in template


def test_get_template_not_found():
    assert get_template("inexistant") is None


def test_generate_html():
    html = generate_contract_html("mise_en_demeure", {
        "nom_creancier": "Dupont SA",
        "nom_debiteur": "Martin SPRL",
        "montant_du": "5.000 EUR",
        "description_dette": "Facture 2026-001",
        "delai_jours": "15",
    })
    assert "Dupont SA" in html
    assert "5.000 EUR" in html
    assert "Mise en demeure" in html


def test_generate_html_missing_vars():
    html = generate_contract_html("bail_bruxelles", {"nom_bailleur": "Test"})
    assert "Test" in html
    assert "[nom_preneur]" in html  # unfilled variables show as placeholders


def test_invalid_template_raises():
    with pytest.raises(ValueError):
        generate_contract_html("fake_template", {})
