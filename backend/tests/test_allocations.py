"""Tests: Loan officer allocations"""
import pytest


@pytest.mark.django_db
class TestAllocations:
    def test_list_allocations(self, auth_client):
        resp = auth_client.get("/api/v1/allocations/")
        assert resp.status_code == 200
        assert "results" in resp.data

    def test_soft_reshuffle(self, auth_client, branch):
        resp = auth_client.post("/api/v1/allocations/soft-reshuffle/", {
            "branch_id": branch.id,
        }, format="json")
        assert resp.status_code in (200, 201, 204)

    def test_hard_reshuffle(self, auth_client, branch):
        resp = auth_client.post("/api/v1/allocations/hard-reshuffle/", {
            "branch_id": branch.id,
        }, format="json")
        assert resp.status_code in (200, 201, 204)
