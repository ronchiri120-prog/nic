"""Tests: Reports and CBK regulatory returns"""
import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestReports:
    def test_branch_performance_report(self, auth_client, branch):
        resp = auth_client.get("/api/v1/reports/branch-performance/")
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_individual_performance_report(self, auth_client):
        resp = auth_client.get("/api/v1/reports/individual-performance/")
        assert resp.status_code == 200

    def test_defaulters_report(self, auth_client):
        resp = auth_client.get("/api/v1/reports/defaulters/")
        assert resp.status_code == 200
        assert "loans" in resp.data or isinstance(resp.data, list)

    def test_dormant_customers_report(self, auth_client):
        resp = auth_client.get("/api/v1/reports/dormant-customers/")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCBKReports:
    def test_mfi01_balance_sheet(self, auth_client):
        resp = auth_client.get("/api/v1/reports/cbk/mfi-01/")
        assert resp.status_code == 200
        assert resp.data["return_type"] == "MFI-01"
        assert "assets" in resp.data
        assert "borrowers" in resp.data

    def test_mfi02_income_statement(self, auth_client):
        today = timezone.now().date()
        resp = auth_client.get(
            "/api/v1/reports/cbk/mfi-02/",
            {"from": str(today.replace(day=1)), "to": str(today)},
        )
        assert resp.status_code == 200
        assert resp.data["return_type"] == "MFI-02"
        assert "income" in resp.data
        assert "lending_activity" in resp.data

    def test_mfi03_portfolio_quality(self, auth_client):
        resp = auth_client.get("/api/v1/reports/cbk/mfi-03/")
        assert resp.status_code == 200
        assert resp.data["return_type"] == "MFI-03"

    def test_mfi04_capital_adequacy(self, auth_client):
        resp = auth_client.get("/api/v1/reports/cbk/mfi-04/")
        assert resp.status_code == 200
        assert resp.data["return_type"] == "MFI-04"
        assert "capital_adequacy_ratio" in resp.data
        assert "cbk_minimum" in resp.data
        assert resp.data["cbk_minimum"] == 10.0
