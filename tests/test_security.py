"""
Tests sécurité — headers HTTP, CORS, PII masking.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestSecurityHeaders:
    """Vérifie que le SecurityHeadersMiddleware injecte bien tous les headers."""

    def _get_headers(self, client):
        r = client.get("/health")
        return r.headers

    def test_hsts_present(self, client):
        h = self._get_headers(client)
        assert "strict-transport-security" in h
        assert "max-age=" in h["strict-transport-security"]

    def test_x_frame_options(self, client):
        h = self._get_headers(client)
        assert "x-frame-options" in h
        assert h["x-frame-options"].upper() == "DENY"

    def test_csp_present(self, client):
        h = self._get_headers(client)
        assert "content-security-policy" in h
        assert "default-src" in h["content-security-policy"]

    def test_x_content_type_options(self, client):
        h = self._get_headers(client)
        assert "x-content-type-options" in h
        assert h["x-content-type-options"] == "nosniff"

    def test_referrer_policy(self, client):
        h = self._get_headers(client)
        assert "referrer-policy" in h

    def test_server_header_masked(self, client):
        """Le header Server ne doit pas exposer uvicorn/fastapi."""
        h = self._get_headers(client)
        server = h.get("server", "").lower()
        assert "uvicorn" not in server
        assert "fastapi" not in server


class TestCORS:
    """Vérifie que le CORS n'autorise jamais le wildcard '*'."""

    def test_no_wildcard_in_allowed_origins(self):
        """Import direct de la config — '*' doit être absent."""
        import importlib
        import api.main as main_module
        # La liste est construite dans main.py, l'assert y est déjà présent
        # On vérifie via introspection de l'app
        cors_middleware = None
        for m in main_module.app.middleware_stack.__class__.__mro__:
            pass  # just confirming app loads
        # Test indirect : la requête OPTIONS avec Origin interdit ne doit pas
        # retourner Access-Control-Allow-Origin: *
        from fastapi.testclient import TestClient
        client = TestClient(main_module.app)
        r = client.options("/health", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        })
        acao = r.headers.get("access-control-allow-origin", "")
        assert acao != "*", "CORS wildcard '*' détecté — sécurité critique"

    def test_known_origin_allowed(self):
        """Un origin Lexavo légitime doit être accepté."""
        import api.main as main_module
        from fastapi.testclient import TestClient
        client = TestClient(main_module.app)
        r = client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        # 200 ou 204 = preflight accepté
        assert r.status_code in (200, 204)


class TestPIIMasking:
    """Vérifie que scrub_pii masque bien les données sensibles."""

    def test_password_masked(self):
        from api.security import scrub_pii
        raw = 'login attempt with {"password": "supersecret123"}'
        result = scrub_pii(raw)
        assert "supersecret123" not in result
        assert "[REDACTED]" in result

    def test_jwt_masked(self):
        from api.security import scrub_pii
        fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0QGxleGF2by5iZSJ9.abc123signature"
        result = scrub_pii(fake_jwt)
        assert fake_jwt not in result
        assert "[JWT_REDACTED]" in result

    def test_bearer_token_masked(self):
        from api.security import scrub_pii
        raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        result = scrub_pii(raw)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_email_partially_masked(self):
        from api.security import scrub_pii
        raw = "user test@lexavo.be logged in"
        result = scrub_pii(raw)
        assert "test@lexavo.be" not in result
        assert "@lexavo.be" in result  # domaine visible, local masqué

    def test_plain_text_unchanged(self):
        from api.security import scrub_pii
        raw = "Demande de renseignement sur le Code civil belge."
        result = scrub_pii(raw)
        assert result == raw

    def test_mask_email_helper(self):
        from api.security import mask_email
        assert mask_email("mamadou@lexavo.be") == "m***@lexavo.be"
        assert mask_email("") == ""
        assert mask_email(None) == ""

    def test_mask_ip_ipv4(self):
        from api.security import mask_ip
        assert mask_ip("192.168.1.42") == "192.168.1.0/24"

    def test_mask_ip_empty(self):
        from api.security import mask_ip
        assert mask_ip(None) == ""
        assert mask_ip("") == ""
