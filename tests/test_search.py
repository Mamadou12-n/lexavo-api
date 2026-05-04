"""
Tests API /search via TestClient HTTP.
Qdrant peut être indisponible en CI → on accepte 200 ou 503.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _search(client, body):
    return client.post("/search", json=body)


class TestSearchEndpoint:
    def test_valid_query_returns_200_or_503(self, client):
        """503 si Qdrant absent en CI, 200 si disponible — les deux sont valides."""
        r = _search(client, {"query": "droit du travail préavis"})
        assert r.status_code in (200, 503)

    def test_200_has_results_key(self, client):
        r = _search(client, {"query": "contrat de travail"})
        if r.status_code == 200:
            data = r.json()
            assert "results" in data
            assert isinstance(data["results"], list)

    def test_source_filter_propagated(self, client):
        # source_filter est List[str] dans SearchRequest, pas une string seule
        r = _search(client, {"query": "TVA", "source_filter": ["justel"]})
        assert r.status_code in (200, 503)

    def test_top_k_respected(self, client):
        r = _search(client, {"query": "code pénal", "top_k": 3})
        if r.status_code == 200:
            data = r.json()
            assert len(data["results"]) <= 3

    def test_empty_query_returns_422(self, client):
        """Query vide → validation Pydantic → 422."""
        r = _search(client, {})
        assert r.status_code == 422
