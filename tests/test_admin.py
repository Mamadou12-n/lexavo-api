"""
Tests endpoint POST /admin/backup.
- Sans auth → 401
- User normal → 403
- User-Agent navigateur → 403
- Admin + CLI → 200
"""
import pytest
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import create_user, _get_conn, _execute, PH
from api.auth import create_token


def _make_admin_headers():
    """Crée un user, le promeut admin via SQL direct, retourne ses headers."""
    email = f"admin_{os.urandom(4).hex()}@lexavo.be"
    user = create_user(
        email=email,
        password_hash="fakehash",
        name="Admin Test",
        language="fr",
    )
    # Promotion admin via SQL (seule voie autorisée selon la règle de sécurité)
    conn = _get_conn()
    try:
        _execute(conn, f"UPDATE users SET role = 'admin' WHERE id = {PH}", (user["id"],))
        conn.commit()
    finally:
        conn.close()
    token = create_token(user["id"], email)
    return {"Authorization": f"Bearer {token}"}


CLI_HEADERS = {"User-Agent": "curl/7.88.1"}
BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


class TestAdminBackup:
    def test_no_auth_returns_401(self, client):
        r = client.post("/admin/backup")
        assert r.status_code == 401

    def test_normal_user_returns_403(self, client, auth_headers):
        r = client.post("/admin/backup", headers={**auth_headers, **CLI_HEADERS})
        assert r.status_code == 403

    def test_admin_browser_ua_returns_403(self, client):
        headers = {**_make_admin_headers(), **BROWSER_HEADERS}
        r = client.post("/admin/backup", headers=headers)
        assert r.status_code == 403

    def test_admin_cli_ua_returns_200(self, client):
        headers = {**_make_admin_headers(), **CLI_HEADERS}
        r = client.post("/admin/backup", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
        assert "backup_path" in data

    def test_admin_no_ua_returns_403(self, client):
        """User-Agent absent → refusé."""
        headers = _make_admin_headers()
        headers.pop("User-Agent", None)
        r = client.post("/admin/backup", headers=headers)
        assert r.status_code == 403
