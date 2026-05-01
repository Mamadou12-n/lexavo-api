"""
Tests endpoints publics — /health et /branches.
Ne requièrent pas d'auth ni de services externes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestHealth:
    def test_health_status_ok(self, client):
        """GET /health doit retourner 200 avec status=ok ou degraded."""
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded")

    def test_health_has_api_version(self, client):
        r = client.get("/health")
        assert "api_version" in r.json()

    def test_health_has_index_key(self, client):
        r = client.get("/health")
        assert "index" in r.json()


class TestBranches:
    def test_branches_status(self, client):
        r = client.get("/branches")
        assert r.status_code == 200

    def test_branches_key_present(self, client):
        r = client.get("/branches")
        assert "branches" in r.json()

    def test_branches_is_list(self, client):
        r = client.get("/branches")
        assert isinstance(r.json()["branches"], list)

    def test_branches_not_empty(self, client):
        r = client.get("/branches")
        assert len(r.json()["branches"]) > 0
