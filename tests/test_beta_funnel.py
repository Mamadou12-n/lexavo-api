"""Tests du funnel beta->paid.

Couvre :
- normalize_lang() + fallback
- load_template() par milestone x langue
- personalize() placeholders
- get_subject() i18n
- days_until_beta_end()
- send_email() : succes, 409 dedup, 400 no-retry, echec 3 retries
- endpoint admin GET /admin/beta-funnel/status
- endpoint admin POST /admin/beta-funnel/trigger (dry_run + milestone invalide)
- endpoint admin POST /admin/beta-funnel/run-daily
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("RATELIMIT_ENABLED", "0")
os.environ.setdefault("LEXAVO_JWT_SECRET", "test-secret-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("LEXAVO_ADMIN_KEY", "admin-test-key")

ADMIN_KEY = "admin-test-key"

from scripts.send_beta_emails import (  # noqa: E402
    normalize_lang,
    load_template,
    personalize,
    get_subject,
    SUBJECTS,
    SUPPORTED_LANGS,
)
from api.beta_funnel import days_until_beta_end  # noqa: E402


# ─── normalize_lang ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("code,expected", [
    ("fr", "fr"),
    ("nl", "nl"),
    ("en", "en"),
    ("de", "de"),
    ("fr-BE", "fr"),
    ("nl-NL", "nl"),
    ("en-US", "en"),
    ("de-DE", "de"),
    ("es", "fr"),
    ("ar", "fr"),
    ("", "fr"),
    (None, "fr"),
    ("FR", "fr"),
])
def test_normalize_lang(code: str | None, expected: str) -> None:
    assert normalize_lang(code) == expected


# ─── load_template ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("milestone", ["j30", "j7", "j0"])
@pytest.mark.parametrize("lang", ["fr", "nl", "en", "de"])
def test_load_template_exists(milestone: str, lang: str) -> None:
    content = load_template(milestone, lang)
    assert len(content) > 100
    assert "Lexavo" in content


def test_load_template_fallback_to_fr_on_unsupported_lang() -> None:
    content = load_template("j30", "es")
    fr_content = load_template("j30", "fr")
    assert content == fr_content


@pytest.mark.parametrize("milestone", ["j30", "j7", "j0"])
def test_load_template_contains_placeholders(milestone: str) -> None:
    for lang in SUPPORTED_LANGS:
        content = load_template(milestone, lang)
        assert "{{NAME}}" in content
        assert "{{EMAIL}}" in content
        assert "{{CHECKOUT_URL}}" in content
        assert "{{UNSUBSCRIBE_URL}}" in content


# ─── personalize ─────────────────────────────────────────────────────────────

def test_personalize_replaces_all_placeholders() -> None:
    tpl = "Bonjour {{NAME}}, email={{EMAIL}}, checkout={{CHECKOUT_URL}}, unsub={{UNSUBSCRIBE_URL}}, end={{BETA_END}}"
    result = personalize(tpl, name="Alice", email="alice@test.be", user_id=42)
    for placeholder in ("{{NAME}}", "{{EMAIL}}", "{{CHECKOUT_URL}}", "{{UNSUBSCRIBE_URL}}", "{{BETA_END}}"):
        assert placeholder not in result
    assert "Alice" in result
    assert "alice@test.be" in result
    assert "42" in result


def test_personalize_empty_name() -> None:
    result = personalize("Bonjour {{NAME}},", name="", email="x@x.be", user_id=1)
    assert "Bonjour ," in result


# ─── get_subject ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("milestone", ["j30", "j7", "j0"])
@pytest.mark.parametrize("lang", ["fr", "nl", "en", "de"])
def test_get_subject_returns_non_empty(milestone: str, lang: str) -> None:
    subject = get_subject(milestone, lang)
    assert len(subject) > 5
    assert "Lexavo" in subject


def test_get_subject_fallback_unsupported_lang() -> None:
    assert get_subject("j30", "es") == SUBJECTS["j30"]["fr"]


def test_get_subject_unknown_milestone() -> None:
    assert "j999" in get_subject("j999", "fr")


# ─── days_until_beta_end ─────────────────────────────────────────────────────

def test_days_until_beta_end_j30() -> None:
    assert days_until_beta_end(date(2026, 9, 1)) == 30


def test_days_until_beta_end_j0() -> None:
    assert days_until_beta_end(date(2026, 10, 1)) == 0


def test_days_until_beta_end_past() -> None:
    assert days_until_beta_end(date(2026, 10, 2)) == -1


# ─── send_email (mock requests) ──────────────────────────────────────────────

def _resp(status_code: int, text: str = "ok") -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    return r


@patch("scripts.send_beta_emails.requests.post")
def test_send_email_success(mock_post: MagicMock) -> None:
    from scripts.send_beta_emails import send_email
    mock_post.return_value = _resp(200)
    assert send_email("a@b.be", "Sujet", "<p>html</p>", "beta-j30/1") is True
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Idempotency-Key"] == "beta-j30/1"


@patch("scripts.send_beta_emails.requests.post")
def test_send_email_409_counts_as_sent(mock_post: MagicMock) -> None:
    from scripts.send_beta_emails import send_email
    mock_post.return_value = _resp(409)
    assert send_email("a@b.be", "Sujet", "<p>html</p>", "beta-j30/1") is True


@patch("scripts.send_beta_emails.requests.post")
def test_send_email_400_no_retry(mock_post: MagicMock) -> None:
    from scripts.send_beta_emails import send_email
    mock_post.return_value = _resp(400, "bad request")
    assert send_email("a@b.be", "Sujet", "<p>html</p>", "beta-j30/1") is False
    assert mock_post.call_count == 1


@patch("scripts.send_beta_emails.time.sleep")
@patch("scripts.send_beta_emails.requests.post")
def test_send_email_retries_on_500(mock_post: MagicMock, mock_sleep: MagicMock) -> None:
    from scripts.send_beta_emails import send_email
    mock_post.return_value = _resp(500, "server error")
    assert send_email("a@b.be", "Sujet", "<p>html</p>", "beta-j30/1") is False
    assert mock_post.call_count == 3


# ─── Endpoints admin ──────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


def test_admin_status_missing_key(client) -> None:
    r = client.get("/admin/beta-funnel/status")
    assert r.status_code in (403, 422)


def test_admin_status_wrong_key(client) -> None:
    r = client.get("/admin/beta-funnel/status", headers={"x-admin-key": "wrong"})
    assert r.status_code == 403


def test_admin_status_ok(client) -> None:
    r = client.get("/admin/beta-funnel/status", headers={"x-admin-key": ADMIN_KEY})
    assert r.status_code == 200
    data = r.json()
    assert "days_until_beta_end" in data
    assert data["beta_end_date"] == "2026-10-01"


def test_admin_trigger_invalid_milestone(client) -> None:
    r = client.post(
        "/admin/beta-funnel/trigger",
        json={"milestone": "j999", "dry_run": True},
        headers={"x-admin-key": ADMIN_KEY},
    )
    assert r.status_code == 400


def test_admin_trigger_dry_run(client) -> None:
    r = client.post(
        "/admin/beta-funnel/trigger",
        json={"milestone": "j30", "dry_run": True},
        headers={"x-admin-key": ADMIN_KEY},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["dry_run"] is True
    assert data["milestone"] == "j30"


@patch("api.routers.beta_funnel.run_daily_beta_funnel")
def test_admin_run_daily(mock_run: MagicMock, client) -> None:
    mock_run.return_value = {
        "today": "2026-09-01",
        "days_until_end": 30,
        "stage_triggered": "j30",
        "j30_sent": 5,
        "j7_sent": 0,
        "j0_sent": 0,
        "errors": [],
    }
    r = client.post("/admin/beta-funnel/run-daily", headers={"x-admin-key": ADMIN_KEY})
    assert r.status_code == 200
    data = r.json()
    assert data["j30_sent"] == 5
    assert data["stage_triggered"] == "j30"
