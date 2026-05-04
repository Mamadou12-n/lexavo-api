"""
Tests API calculateurs via TestClient HTTP — couverture endpoints
POST /calculators/notice-period, /alimony, /succession, /indexation-loyer
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestNoticePeriodEndpoint:
    def test_valid_returns_result(self, client, auth_headers):
        r = client.post(
            "/calculators/notice-period",
            json={"years": 5, "monthly_salary": 3000},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        # Réponse enveloppée : result + details
        assert "result" in data
        assert data["result"] > 0
        assert "details" in data
        assert data["details"]["weeks"] == 18

    def test_missing_salary_returns_400(self, client, auth_headers):
        r = client.post(
            "/calculators/notice-period",
            json={"years": 3, "monthly_salary": 0},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_no_auth_returns_401(self, client):
        r = client.post(
            "/calculators/notice-period",
            json={"years": 5, "monthly_salary": 3000},
        )
        assert r.status_code == 401

    def test_invalid_string_params_returns_400(self, client, auth_headers):
        r = client.post(
            "/calculators/notice-period",
            json={"years": "abc", "monthly_salary": "xyz"},
            headers=auth_headers,
        )
        assert r.status_code == 400


class TestAlimonyEndpoint:
    def test_valid_returns_result(self, client, auth_headers):
        r = client.post(
            "/calculators/alimony",
            json={"income_high": 4000, "income_low": 1500, "children": 2},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        # Réponse enveloppée : result (montant mensuel) + details
        assert "result" in data
        assert data["result"] > 0

    def test_no_auth_returns_401(self, client):
        r = client.post(
            "/calculators/alimony",
            json={"income_high": 4000, "income_low": 1500},
        )
        assert r.status_code == 401


class TestSuccessionEndpoint:
    def test_brussels_direct_line_100k(self, client, auth_headers):
        r = client.post(
            "/calculators/succession",
            json={"region": "bruxelles", "amount": 100000, "relationship": "direct_line"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        # Réponse enveloppée : result = droits de succession en €
        assert "result" in data
        assert data["result"] == pytest.approx(5500.0, abs=50)
        assert data["details"]["region"] == "bruxelles"

    def test_wallonie_sibling_50k(self, client, auth_headers):
        r = client.post(
            "/calculators/succession",
            json={"region": "wallonie", "amount": 50000, "relationship": "siblings"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "result" in data
        assert data["result"] > 0

    def test_fr_mapping_enfant(self, client, auth_headers):
        """Le mot 'enfant' doit être mappé vers direct_line."""
        r = client.post(
            "/calculators/succession",
            json={"region": "bruxelles", "amount": 100000, "relationship": "enfant"},
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_invalid_region_raises_or_returns_error(self, client, auth_headers):
        """region='paris' lève ValueError → 500 non géré ou exception levée par TestClient."""
        from fastapi.testclient import TestClient
        from api.main import app
        safe_client = TestClient(app, raise_server_exceptions=False)
        r = safe_client.post(
            "/calculators/succession",
            json={"region": "paris", "amount": 100000},
            headers=auth_headers,
        )
        assert r.status_code in (400, 422, 500)

    def test_no_auth_returns_401(self, client):
        r = client.post(
            "/calculators/succession",
            json={"region": "bruxelles", "amount": 100000},
        )
        assert r.status_code == 401


class TestIndexationLoyerEndpoint:
    def test_valid_1000_110_115(self, client, auth_headers):
        r = client.post(
            "/calculators/indexation-loyer",
            json={"loyer_base": 1000.0, "indice_depart": 110.0, "indice_nouveau": 115.5},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        # Réponse enveloppée : result = loyer indexé en €
        assert "result" in data
        assert data["result"] == pytest.approx(1050.0, abs=1.0)
        assert data["details"]["augmentation"] == pytest.approx(50.0, abs=1.0)

    def test_no_auth_returns_401(self, client):
        r = client.post(
            "/calculators/indexation-loyer",
            json={"loyer_base": 1000.0, "indice_depart": 110.0, "indice_nouveau": 115.0},
        )
        assert r.status_code == 401
