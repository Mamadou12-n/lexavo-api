import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.features.emergency import get_categories, create_emergency_request

def test_get_categories():
    cats = get_categories()
    assert len(cats) >= 7
    assert any(c["id"] == "garde_a_vue" for c in cats)

def test_create_request():
    result = create_emergency_request(
        user_id=1, category="licenciement",
        description="Mon employeur m'a licencie ce matin sans preavis ni motif grave",
        phone="+32470123456", city="Bruxelles"
    )
    assert result["status"] == "pending"
    assert result["price_cents"] == 4900
    assert "request_id" in result

def test_short_description():
    with pytest.raises(ValueError, match="minimum 20"):
        create_emergency_request(1, "autre", "help", "+32470123456", "Bruxelles")

def test_missing_phone():
    with pytest.raises(ValueError, match="telephone"):
        create_emergency_request(1, "autre", "J'ai besoin d'aide juridique urgente", "", "Bxl")
