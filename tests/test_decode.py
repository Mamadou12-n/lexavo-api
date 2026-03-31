import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.features.decode import decode_document


def test_decode_returns_plain_language():
    text = """
    AVIS D'IMPOSITION - EXERCICE D'IMPOSITION 2025
    SPF FINANCES - Administration generale de la Fiscalite
    Conformement aux articles 359 et suivants du CIR 1992,
    le revenu imposable globalement s'eleve a 45.000,00 EUR.
    La quotite exemptee d'impot est fixee a 10.160,00 EUR
    (art. 131 CIR 1992).
    """
    result = decode_document(text, mock=True)
    assert "plain_language" in result
    assert len(result["plain_language"]) > 20
    assert "key_points" in result
    assert isinstance(result["key_points"], list)


def test_decode_returns_actions():
    text = "Notification de decision du SPF Finances concernant votre declaration fiscale pour l'exercice 2025."
    result = decode_document(text, mock=True)
    assert "actions_required" in result
    assert isinstance(result["actions_required"], list)


def test_decode_rejects_empty():
    with pytest.raises(ValueError):
        decode_document("", mock=True)


def test_decode_rejects_short():
    with pytest.raises(ValueError):
        decode_document("trop court", mock=True)
