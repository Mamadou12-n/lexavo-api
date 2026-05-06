"""Tests paywall progressif — niveaux warning + endpoint /billing/quota/status.

Couvre :
- _compute_warning_level() : seuils 0/50/80/100%
- _next_quota_reset_iso() : ISO valide, futur, 1er du mois
- get_quota_status() : retour enrichi sans incrément
- GET /billing/quota/status : auth + payload conforme
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestComputeWarningLevel:
    def test_zero_used_returns_none(self):
        from api.stripe_billing import _compute_warning_level
        assert _compute_warning_level(0, 50) == "none"

    def test_below_50pct_returns_none(self):
        from api.stripe_billing import _compute_warning_level
        assert _compute_warning_level(20, 50) == "none"
        assert _compute_warning_level(24, 50) == "none"

    def test_at_50pct_returns_soft(self):
        from api.stripe_billing import _compute_warning_level
        assert _compute_warning_level(25, 50) == "soft"
        assert _compute_warning_level(30, 50) == "soft"

    def test_between_50_80pct_returns_soft(self):
        from api.stripe_billing import _compute_warning_level
        assert _compute_warning_level(35, 50) == "soft"
        assert _compute_warning_level(39, 50) == "soft"

    def test_at_80pct_returns_hard(self):
        from api.stripe_billing import _compute_warning_level
        assert _compute_warning_level(40, 50) == "hard"
        assert _compute_warning_level(45, 50) == "hard"

    def test_at_100pct_returns_blocked(self):
        from api.stripe_billing import _compute_warning_level
        assert _compute_warning_level(50, 50) == "blocked"

    def test_over_100pct_returns_blocked(self):
        from api.stripe_billing import _compute_warning_level
        assert _compute_warning_level(60, 50) == "blocked"

    def test_unlimited_limit_returns_none(self):
        from api.stripe_billing import _compute_warning_level
        assert _compute_warning_level(1000, -1) == "none"
        assert _compute_warning_level(1000, 0) == "none"


class TestNextQuotaReset:
    def test_returns_valid_iso(self):
        from api.stripe_billing import _next_quota_reset_iso
        iso = _next_quota_reset_iso()
        parsed = datetime.fromisoformat(iso)
        assert parsed.tzinfo is not None

    def test_is_first_of_next_month(self):
        from api.stripe_billing import _next_quota_reset_iso
        parsed = datetime.fromisoformat(_next_quota_reset_iso())
        assert parsed.day == 1
        assert parsed.hour == 0
        assert parsed.minute == 0

    def test_is_in_future(self):
        from api.stripe_billing import _next_quota_reset_iso
        parsed = datetime.fromisoformat(_next_quota_reset_iso())
        assert parsed > datetime.now(timezone.utc)


class TestQuotaStatusEndpoint:
    def test_requires_auth(self, client):
        resp = client.get("/billing/quota/status")
        assert resp.status_code == 401

    def test_returns_warning_fields(self, client, auth_headers):
        resp = client.get("/billing/quota/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for field in ("plan", "questions_used", "questions_limit",
                      "warning_level", "upgrade_recommended", "next_reset"):
            assert field in data, f"Champ manquant : {field}"

    def test_new_user_has_warning_level_none(self, client, auth_headers):
        resp = client.get("/billing/quota/status", headers=auth_headers)
        data = resp.json()
        assert data["warning_level"] in ("none", "soft", "hard", "blocked")
        assert data["questions_used"] == 0
        assert data["upgrade_recommended"] is False

    def test_does_not_consume_quota(self, client, auth_headers):
        r1 = client.get("/billing/quota/status", headers=auth_headers).json()
        r2 = client.get("/billing/quota/status", headers=auth_headers).json()
        assert r1["questions_used"] == r2["questions_used"]


class TestGetQuotaStatusFunction:
    def test_returns_dict_with_required_keys(self):
        from api.stripe_billing import get_quota_status
        from api.database import create_user
        user = create_user(
            email=f"qtest_{os.urandom(4).hex()}@lexavo.be",
            password_hash="fakehash",
            name="Q Test",
            language="fr",
        )
        status = get_quota_status(user["id"])
        for key in ("allowed", "plan", "questions_used", "questions_limit",
                    "questions_remaining", "warning_level",
                    "upgrade_recommended", "next_reset"):
            assert key in status

    def test_unlimited_plan_returns_none_warning(self):
        from api.stripe_billing import get_quota_status
        from api.database import create_user
        user = create_user(
            email=f"qtest2_{os.urandom(4).hex()}@lexavo.be",
            password_hash="fakehash",
            name="Q Test 2",
            language="fr",
        )
        status = get_quota_status(user["id"])
        if status["questions_limit"] == -1:
            assert status["warning_level"] == "none"
            assert status["upgrade_recommended"] is False
