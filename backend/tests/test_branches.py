"""Tests: Branch management"""
import pytest


@pytest.mark.django_db
class TestBranches:
    def test_list_branches(self, auth_client, branch):
        resp = auth_client.get("/api/v1/branches/")
        assert resp.status_code == 200
        names = [b["name"] for b in (resp.data.get("results") or resp.data)]
        assert branch.name in names

    def test_create_branch(self, auth_client):
        resp = auth_client.post("/api/v1/branches/", {
            "name": "Nakuru Branch",
            "code": "NKR",
            "disb_target": 1500000,
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["code"] == "NKR"

    def test_duplicate_code_rejected(self, auth_client, branch):
        resp = auth_client.post("/api/v1/branches/", {
            "name": "Duplicate",
            "code": branch.code,
            "disb_target": 500000,
        }, format="json")
        assert resp.status_code == 400

    def test_branch_performance_report(self, auth_client, branch):
        resp = auth_client.get("/api/v1/reports/branch-performance/")
        assert resp.status_code == 200
        assert isinstance(resp.data, list)
