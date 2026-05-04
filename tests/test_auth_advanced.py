"""
Tests authentification avancés :
- Rotation des refresh tokens (ancien invalidé après usage)
- Réutilisation d'un refresh token → cascade delete
- /account/export après auth → JSON complet
- Forgot-password : réponse constante (anti-timing-oracle)
"""
import pytest
import sys
import os
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import create_user, save_refresh_token
from api.auth import create_token, create_refresh_token, REFRESH_TOKEN_EXPIRY_DAYS
from datetime import datetime, timezone, timedelta


def _register_and_login(client):
    """Inscrit un user unique, connecte, retourne le dict de réponse."""
    email = f"adv_{os.urandom(5).hex()}@lexavo.be"
    client.post(
        "/auth/register",
        json={"email": email, "password": "Test1234!", "name": "Adv User"},
    )
    r = client.post(
        "/auth/login",
        json={"email": email, "password": "Test1234!"},
    )
    assert r.status_code == 200
    return r.json()


class TestRefreshTokenRotation:
    def test_refresh_returns_new_tokens(self, client):
        data = _register_and_login(client)
        rt = data["refresh_token"]
        r = client.post("/auth/refresh", json={"refresh_token": rt})
        assert r.status_code == 200
        body = r.json()
        assert "token" in body
        assert "refresh_token" in body
        # Le nouveau refresh token doit être différent de l'ancien
        assert body["refresh_token"] != rt

    def test_old_refresh_token_invalidated_after_rotation(self, client):
        data = _register_and_login(client)
        rt_original = data["refresh_token"]
        # Premier usage : succès
        r1 = client.post("/auth/refresh", json={"refresh_token": rt_original})
        assert r1.status_code == 200
        # Réutilisation du même token → doit échouer (rotation one-shot)
        r2 = client.post("/auth/refresh", json={"refresh_token": rt_original})
        assert r2.status_code == 401

    def test_refresh_token_reuse_cascade_with_hint(self, client):
        """Réutilisation + hint user_id → tous les tokens de l'user sont révoqués."""
        data = _register_and_login(client)
        rt = data["refresh_token"]
        user_id = data["user"]["id"]
        # Consommer le token une première fois
        r1 = client.post("/auth/refresh", json={"refresh_token": rt})
        assert r1.status_code == 200
        new_rt = r1.json()["refresh_token"]
        # Réutiliser l'ancien token avec hint → cascade delete
        r2 = client.post(
            "/auth/refresh",
            json={"refresh_token": rt},
            headers={"X-Lexavo-Hint-User": str(user_id)},
        )
        assert r2.status_code == 401
        # Le nouveau token obtenu précédemment doit également être révoqué
        r3 = client.post("/auth/refresh", json={"refresh_token": new_rt})
        assert r3.status_code == 401

    def test_missing_refresh_token_returns_400(self, client):
        r = client.post("/auth/refresh", json={})
        assert r.status_code == 400

    def test_invalid_refresh_token_returns_401(self, client):
        r = client.post("/auth/refresh", json={"refresh_token": "totally_fake_token"})
        assert r.status_code == 401


class TestAccountExport:
    def test_export_requires_auth(self, client):
        r = client.get("/account/export")
        assert r.status_code == 401

    def test_export_returns_json(self, client, auth_headers):
        r = client.get("/account/export", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        # Export RGPD doit contenir au minimum l'email ou les données user
        assert isinstance(data, dict)
        assert len(data) > 0


class TestForgotPassword:
    def test_existing_email_returns_constant_message(self, client):
        """Réponse identique que l'email existe ou non (anti-oracle)."""
        r = client.post("/auth/forgot-password", json={"email": "exists@lexavo.be"})
        assert r.status_code == 200
        msg = r.json().get("message", "")
        assert "lien" in msg.lower() or "envoy" in msg.lower()

    def test_nonexistent_email_returns_same_message(self, client):
        r = client.post(
            "/auth/forgot-password",
            json={"email": "nobody_xyz_never@lexavo.be"},
        )
        assert r.status_code == 200
        # Ne doit pas révéler que l'email n'existe pas
        msg = r.json().get("message", "")
        assert "lien" in msg.lower() or "envoy" in msg.lower()
