"""
Tests endpoints /branches, /defend/categories, /student/branches.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBranchesEndpoints:
    def test_get_branches_returns_15(self, client):
        r = client.get("/branches")
        assert r.status_code == 200
        data = r.json()
        assert "branches" in data
        assert len(data["branches"]) == 15

    def test_get_branches_total_field(self, client):
        r = client.get("/branches")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == len(data["branches"])

    def test_defend_categories_returns_list(self, client):
        r = client.get("/defend/categories")
        assert r.status_code == 200
        data = r.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) > 0

    def test_student_branches_returns_list(self, client):
        r = client.get("/student/branches")
        assert r.status_code == 200
        data = r.json()
        assert "branches" in data
        assert len(data["branches"]) > 0
