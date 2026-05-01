"""
Tests RGPD — endpoints suppression et export de compte.
Vérifie que les droits d'accès sont bien appliqués (401 sans auth).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestAccountDeletion:
    def test_delete_account_no_auth(self, client):
        """DELETE /account sans token doit retourner 401."""
        r = client.delete("/account")
        assert r.status_code == 401

    def test_delete_account_invalid_token(self, client):
        r = client.delete("/account", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401

    def test_delete_account_authenticated(self, client, auth_headers):
        """DELETE /account avec un token valide doit retourner 204."""
        r = client.delete("/account", headers=auth_headers)
        # 204 No Content = suppression réussie
        assert r.status_code == 204


class TestAccountExport:
    def test_export_no_auth(self, client):
        """GET /account/export sans token doit retourner 401."""
        r = client.get("/account/export")
        assert r.status_code == 401

    def test_export_invalid_token(self, client):
        r = client.get("/account/export", headers={"Authorization": "Bearer bad.token"})
        assert r.status_code == 401

    def test_export_authenticated(self, client, auth_headers):
        """GET /account/export avec token valide doit retourner 200 + données."""
        r = client.get("/account/export", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        # Les données exportées ne doivent jamais contenir le mot de passe hashé
        export_str = str(data)
        assert "password_hash" not in export_str
        assert "password" not in export_str.lower() or "password_hash" not in export_str
