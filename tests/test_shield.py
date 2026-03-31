import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.features.shield import analyze_contract_text, detect_contract_type


def test_analyze_contract_returns_verdict():
    text = """
    CONTRAT DE BAIL DE RESIDENCE PRINCIPALE
    Entre les soussignes :
    Le bailleur : M. Dupont, domicilie a 1000 Bruxelles
    Le preneur : M. Martin, domicilie a 1050 Ixelles
    Article 1 - Objet
    Le bailleur donne en location l'appartement situe au
    Rue de la Loi 15, 1000 Bruxelles.
    Article 2 - Duree
    Le bail est conclu pour une duree de 9 ans.
    Article 3 - Loyer
    Le loyer mensuel est fixe a 850 euros.
    """
    result = analyze_contract_text(text, mock=True)
    assert result["verdict"] in ("green", "orange", "red")
    assert len(result["summary"]) > 10
    assert isinstance(result["clauses"], list)


def test_analyze_detects_contract_type():
    text = "CONTRAT DE TRAVAIL a duree indeterminee entre l'employeur et le travailleur pour un salaire de 3000 euros"
    result = analyze_contract_text(text, mock=True)
    assert result["contract_type_detected"] in ("travail", "bail", "vente", "general", None)


def test_analyze_rejects_short_text():
    with pytest.raises(ValueError, match="trop court"):
        analyze_contract_text("texte court", mock=True)


def test_detect_contract_type_bail():
    assert detect_contract_type("Le bailleur donne en location le loyer est de 850 euros au preneur") == "bail"


def test_detect_contract_type_travail():
    assert detect_contract_type("Contrat de travail entre employeur et travailleur salaire licenciement") == "travail"


def test_detect_contract_type_unknown():
    assert detect_contract_type("Un texte sans rapport avec le droit") == "general"
