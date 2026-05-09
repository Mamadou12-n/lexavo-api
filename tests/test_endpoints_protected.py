"""
Tests endpoints protégés — vérifie que les routes sensibles
retournent 401 sans token valide.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestCalculatorsProtected:
    def test_notice_period_no_auth(self, client):
        r = client.post("/calculators/notice-period", json={})
        assert r.status_code == 401

    def test_alimony_no_auth(self, client):
        r = client.post("/calculators/alimony", json={})
        assert r.status_code == 401

    def test_succession_no_auth(self, client):
        r = client.post("/calculators/succession", json={})
        assert r.status_code == 401

    def test_indexation_loyer_no_auth(self, client):
        r = client.post("/calculators/indexation-loyer", json={})
        assert r.status_code == 401


class TestHeritageProtected:
    def test_heritage_guide_no_auth(self, client):
        r = client.post("/heritage/guide", json={})
        # endpoint heritage — 401 si non authentifié
        assert r.status_code in (401, 404)


class TestDefendProtected:
    def test_defend_no_auth(self, client):
        r = client.post("/defend/generate", json={})
        assert r.status_code in (401, 404)


class TestShieldProtected:
    def test_shield_analyze_no_auth(self, client):
        r = client.post("/shield/analyze", json={"text": "contrat test"})
        # 503 si Depends(get_api_key) eval avant auth (ANTHROPIC_API_KEY absent en test)
        assert r.status_code in (401, 503)

    def test_shield_history_no_auth(self, client):
        r = client.get("/shield/history")
        assert r.status_code == 401


class TestConversationsProtected:
    def test_list_conversations_no_auth(self, client):
        r = client.get("/conversations")
        assert r.status_code == 401

    def test_create_conversation_no_auth(self, client):
        r = client.post("/conversations", json={"title": "test"})
        assert r.status_code == 401


class TestBillingProtected:
    def test_subscription_no_auth(self, client):
        r = client.get("/billing/subscription")
        assert r.status_code == 401

    def test_checkout_no_auth(self, client):
        r = client.post("/billing/checkout", json={"plan": "pro"})
        assert r.status_code == 401

    def test_portal_no_auth(self, client):
        r = client.post("/billing/portal", json={})
        assert r.status_code == 401
