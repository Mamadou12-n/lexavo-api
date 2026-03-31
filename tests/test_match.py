import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.features.match import find_matching_lawyers

def test_find_lawyers_returns_matches():
    result = find_matching_lawyers("Mon proprietaire refuse de rendre la garantie locative de mon bail", mock=True)
    assert "matches" in result
    assert isinstance(result["matches"], list)

def test_short_description():
    with pytest.raises(ValueError, match="trop courte"):
        find_matching_lawyers("test", mock=True)

def test_has_disclaimer():
    result = find_matching_lawyers("Probleme de licenciement abusif par mon employeur", mock=True)
    assert "disclaimer" in result
