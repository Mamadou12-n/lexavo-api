import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.features.heritage import generate_heritage_guide

def test_basic_guide():
    guide = generate_heritage_guide(region="bruxelles")
    assert len(guide["steps"]) == 4
    assert guide["region"] == "bruxelles"
    assert "regional_info" in guide

def test_with_estimated_value():
    guide = generate_heritage_guide(region="wallonie", estimated_value=200000)
    assert "estimated_duties" in guide
    assert guide["estimated_duties"]["total_duty"] > 0

def test_with_testament():
    guide = generate_heritage_guide(region="flandre", has_testament=True)
    assert any("testament" in n for n in guide["notes"])

def test_with_real_estate():
    guide = generate_heritage_guide(region="bruxelles", has_real_estate=True)
    assert any("notaire" in n.lower() for n in guide["notes"])

def test_invalid_region():
    with pytest.raises(ValueError, match="Region"):
        generate_heritage_guide(region="paris")

def test_all_regions():
    for region in ["bruxelles", "wallonie", "flandre"]:
        guide = generate_heritage_guide(region=region)
        assert guide["region"] == region
