import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.features.alerts import get_alert_domains, save_preferences, get_alert_feed

def test_get_domains():
    domains = get_alert_domains()
    assert len(domains) == 8
    assert all("id" in d and "label" in d for d in domains)

def test_save_preferences():
    result = save_preferences(user_id=1, domains=["travail", "fiscal", "invalid"])
    assert "travail" in result["domains"]
    assert "fiscal" in result["domains"]
    assert "invalid" not in result["domains"]

def test_get_feed_filtered():
    feed = get_alert_feed(domains=["travail"])
    assert all(a["domain"] == "travail" for a in feed)

def test_get_feed_all():
    feed = get_alert_feed(domains=[])
    assert len(feed) > 0
