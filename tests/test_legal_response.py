import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.features.legal_response import generate_response


def test_generate_response_mock():
    text = "Monsieur, suite a votre retard de paiement du loyer de mars 2026, je vous mets en demeure de payer sous 15 jours."
    result = generate_response(text, mock=True)
    assert "response_letter" in result
    assert len(result["response_letter"]) > 50
    assert result["tone"] in ("formal", "firm", "conciliatory")
    assert "disclaimer" in result


def test_response_has_legal_references():
    text = "Vous etes licencie pour motif grave avec effet immediat a compter de ce jour."
    result = generate_response(text, mock=True)
    assert "legal_references" in result
    assert isinstance(result["legal_references"], list)


def test_response_has_next_steps():
    text = "La banque vous informe de la cloture de votre compte dans les 30 jours."
    result = generate_response(text, mock=True)
    assert "next_steps" in result
    assert isinstance(result["next_steps"], list)


def test_rejects_short_text():
    with pytest.raises(ValueError, match="trop court"):
        generate_response("Bonjour", mock=True)


def test_response_includes_disclaimer():
    text = "Nous vous informons de l'augmentation de votre loyer de 15% a compter du mois prochain."
    result = generate_response(text, mock=True)
    assert "acte d'avocat" in result["disclaimer"]
