"""
Tests API /heritage/guide via TestClient HTTP.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHeritageGuideEndpoint:
    def test_direct_line_returns_guide(self, client, auth_headers):
        r = client.post(
            "/heritage/guide",
            json={"region": "bruxelles", "relationship": "direct_line"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "steps" in data
        assert len(data["steps"]) > 0

    def test_fr_mapping_enfant(self, client, auth_headers):
        """'enfant' doit être mappé vers direct_line sans erreur."""
        r = client.post(
            "/heritage/guide",
            json={"region": "bruxelles", "relationship": "enfant"},
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_fr_mapping_conjoint(self, client, auth_headers):
        r = client.post(
            "/heritage/guide",
            json={"region": "wallonie", "relationship": "conjoint"},
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_fr_mapping_frere(self, client, auth_headers):
        r = client.post(
            "/heritage/guide",
            json={"region": "flandre", "relationship": "frère"},
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_invalid_region_returns_400(self, client, auth_headers):
        r = client.post(
            "/heritage/guide",
            json={"region": "paris"},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_no_auth_returns_401(self, client):
        r = client.post(
            "/heritage/guide",
            json={"region": "bruxelles"},
        )
        assert r.status_code == 401

    def test_with_estimated_value_returns_duties(self, client, auth_headers):
        r = client.post(
            "/heritage/guide",
            json={"region": "bruxelles", "estimated_value": 200000},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "estimated_duties" in data
        # estimated_duties est une réponse enveloppée : result = montant des droits
        assert data["estimated_duties"]["result"] > 0
