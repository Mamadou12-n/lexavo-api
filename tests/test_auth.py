"""
Tests d'intégration — Endpoints d'authentification (FastAPI TestClient).
Couvre : register, login, /auth/me, JWT validation.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestRegister:
    def test_register_success(self, client):
        email = f"reg_{os.urandom(4).hex()}@lexavo.be"
        resp = client.post("/auth/register", json={
            "email": email,
            "password": "password123",
            "name": "Alice Test",
            "language": "fr",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["email"] == email
        assert data["user"]["name"] == "Alice Test"
        assert "password" not in data["user"]

    def test_register_duplicate_email(self, client):
        email = f"dup_{os.urandom(4).hex()}@lexavo.be"
        payload = {"email": email, "password": "password123", "name": "Bob", "language": "fr"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code in (400, 409)

    def test_register_missing_email(self, client):
        resp = client.post("/auth/register", json={
            "password": "password123",
            "name": "No Email",
            "language": "fr",
        })
        assert resp.status_code == 422

    def test_register_password_too_short(self, client):
        resp = client.post("/auth/register", json={
            "email": f"short_{os.urandom(4).hex()}@lexavo.be",
            "password": "abc",   # < 6 chars — rejeté par le modèle Pydantic
            "name": "Short Pass",
            "language": "fr",
        })
        assert resp.status_code == 422

    def test_register_returns_valid_jwt(self, client):
        resp = client.post("/auth/register", json={
            "email": f"jwt_{os.urandom(4).hex()}@lexavo.be",
            "password": "secure123",
            "name": "JWT Test",
            "language": "fr",
        })
        assert resp.status_code == 200
        token = resp.json()["token"]
        # Utiliser le token pour /auth/me
        me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200


class TestLogin:
    def test_login_success(self, client):
        email = f"login_{os.urandom(4).hex()}@lexavo.be"
        password = "loginpass123"
        client.post("/auth/register", json={
            "email": email, "password": password, "name": "Login User", "language": "fr",
        })
        resp = client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["email"] == email

    def test_login_wrong_password(self, client):
        email = f"wrong_{os.urandom(4).hex()}@lexavo.be"
        client.post("/auth/register", json={
            "email": email, "password": "correct_pass", "name": "Wrong", "language": "fr",
        })
        resp = client.post("/auth/login", json={"email": email, "password": "wrong_pass"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/auth/login", json={
            "email": "nobody@lexavo.be", "password": "whatever123",
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", json={"email": "only@email.be"})
        assert resp.status_code == 422


class TestMe:
    def test_me_authenticated(self, client, auth_headers):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "email" in data
        assert "password" not in data

    def test_me_no_token(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer this.is.invalid"})
        assert resp.status_code == 401

    def test_me_malformed_header(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "NotBearer abc"})
        assert resp.status_code == 401
