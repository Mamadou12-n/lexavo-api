"""Tests SEO programmatique Lexavo — 6 tests sur les routes HTML."""

import pytest
from fastapi.testclient import TestClient


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _html(response) -> str:
    """Retourne le corps de la réponse décodé."""
    return response.content.decode("utf-8", errors="replace")


# ─── Tests calculateurs ───────────────────────────────────────────────────────

def test_calcul_preavis_returns_html(client: TestClient):
    """GET /calcul/preavis-licenciement → 200 HTML avec le bon H1."""
    resp = client.get("/calcul/preavis-licenciement")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = _html(resp)
    assert "pr&#233;avis" in body.lower() or "préavis" in body.lower() or "preavis" in body.lower()
    assert "CCT" in body
    assert "Lexavo" in body


def test_calcul_pension_returns_html(client: TestClient):
    """GET /calcul/pension-alimentaire → 200 HTML avec le bon H1."""
    resp = client.get("/calcul/pension-alimentaire")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = _html(resp)
    assert "pension" in body.lower()
    assert "renard" in body.lower() or "Renard" in body
    assert "Lexavo" in body


def test_calcul_succession_returns_html(client: TestClient):
    """GET /calcul/droits-succession → 200 HTML avec le bon H1."""
    resp = client.get("/calcul/droits-succession")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = _html(resp)
    assert "succession" in body.lower()
    assert "bruxelles" in body.lower() or "wallonie" in body.lower()
    assert "Lexavo" in body


def test_avocats_ville_returns_html(client: TestClient):
    """GET /avocats/Bruxelles → 200 HTML avec liste d'avocats."""
    resp = client.get("/avocats/Bruxelles")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = _html(resp)
    assert "bruxelles" in body.lower()
    assert "avocat" in body.lower()
    assert "Lexavo" in body


def test_sitemap_xml(client: TestClient):
    """GET /sitemap.xml → 200 XML valide avec les URLs SEO."""
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "xml" in resp.headers["content-type"]
    body = _html(resp)
    assert '<?xml' in body
    assert '<urlset' in body
    assert '/calcul/preavis-licenciement' in body
    assert '/calcul/pension-alimentaire' in body
    assert '/calcul/droits-succession' in body
    assert '/avocats/' in body
    assert '/modeles/' in body


def test_robots_txt(client: TestClient):
    """GET /robots.txt → 200 texte avec directives correctes."""
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    body = _html(resp)
    assert "User-agent: *" in body
    assert "Allow: /" in body
    assert "Sitemap: https://lexavo.be/sitemap.xml" in body
    assert "Disallow: /auth/" in body
