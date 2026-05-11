"""Tests: Asset finance (logbook loans)"""
import pytest


@pytest.mark.django_db
class TestAssets:
    def test_register_asset(self, auth_client, customer):
        resp = auth_client.post("/api/v1/assets/", {
            "customer":     customer.id,
            "category":     "VEHICLE",
            "make":         "Toyota",
            "model":        "Prado",
            "year":         2020,
            "reg_number":   "KDA 001X",
            "logbook_no":   "LBK/0001/2020",
            "valuation":    "3500000",
            "valued_by":    "Auto Valuers Ltd",
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["asset_id"].startswith("AST-")
        assert float(resp.data["valuation"]) == 3500000
        assert resp.data["ltv"] is not None

    def test_asset_list(self, auth_client):
        resp = auth_client.get("/api/v1/assets/")
        assert resp.status_code == 200
        assert "results" in resp.data

    def test_asset_category_filter(self, auth_client, customer):
        auth_client.post("/api/v1/assets/", {
            "customer": customer.id, "category": "LAND",
            "valuation": "5000000", "valued_by": "Valuers",
        }, format="json")
        resp = auth_client.get("/api/v1/assets/?category=LAND")
        assert resp.status_code == 200
        results = resp.data.get("results", [])
        assert all(a["category"] == "LAND" for a in results)


@pytest.mark.django_db
class TestCreditScoring:
    def test_credit_score_new_customer(self, auth_client, customer):
        resp = auth_client.post("/api/v1/loans/credit-score/", {
            "customer_id": customer.id,
            "loan_amount": 50000,
        }, format="json")
        assert resp.status_code == 200
        assert 0 <= resp.data["score"] <= 100
        assert resp.data["risk_grade"] is not None
        assert resp.data["recommendation"] is not None
        assert isinstance(resp.data["breakdown"], list)
        assert len(resp.data["breakdown"]) == 7

    def test_blacklisted_customer_scores_zero(self, auth_client, customer):
        customer.status = "BLACKLISTED"
        customer.save()
        resp = auth_client.post("/api/v1/loans/credit-score/", {
            "customer_id": customer.id, "loan_amount": 50000,
        }, format="json")
        assert resp.status_code == 200
        assert resp.data["score"] == 0
        assert resp.data["approved"] is False
        assert any("BLACKLISTED" in f for f in resp.data["flags"])

    def test_score_persisted_to_customer(self, auth_client, customer):
        auth_client.post("/api/v1/loans/credit-score/", {
            "customer_id": customer.id, "loan_amount": 30000,
        }, format="json")
        customer.refresh_from_db()
        assert customer.credit_score is not None
        assert customer.credit_score >= 0
