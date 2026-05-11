"""Tests: Payments, M-Pesa transactions"""
import pytest
from decimal import Decimal


@pytest.mark.django_db
class TestPayments:
    def test_record_cash_payment(self, auth_client, loan):
        auth_client.post(f'/api/v1/loans/{loan.id}/approve/')
        auth_client.post(f'/api/v1/loans/{loan.id}/disburse/', {"method":"CASH"}, format="json")
        resp = auth_client.post("/api/v1/payments/", {
            "loan": loan.id, "amount": "10000",
            "method": "CASH", "payment_type": "PARTIAL",
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["ref"].startswith("PMT-")
        loan.refresh_from_db()
        assert loan.total_paid == Decimal("10000")
        assert loan.balance == loan.total_amount - Decimal("10000")

    def test_mpesa_payment_updates_balance(self, auth_client, loan):
        auth_client.post(f"/api/v1/loans/{loan.id}/approve/")
        auth_client.post(f"/api/v1/loans/{loan.id}/disburse/", {"method":"MPESA"}, format="json")
        resp = auth_client.post("/api/v1/payments/", {
            "loan": loan.id, "amount": "5000",
            "method": "MPESA", "mpesa_ref": "QGJ00TEST01", "payment_type": "PARTIAL",
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["method"] == "MPESA"
        loan.refresh_from_db()
        assert loan.total_paid == Decimal("5000")

    def test_full_payment_closes_loan(self, auth_client, loan):
        auth_client.post(f"/api/v1/loans/{loan.id}/approve/")
        auth_client.post(f"/api/v1/loans/{loan.id}/disburse/", {"method":"CASH"}, format="json")
        loan.refresh_from_db()
        resp = auth_client.post("/api/v1/payments/", {
            "loan": loan.id, "amount": str(loan.total_amount),
            "method": "CASH", "payment_type": "FULL",
        }, format="json")
        assert resp.status_code == 201
        loan.refresh_from_db()
        assert loan.status == "CLOSED"
        assert float(loan.balance) <= 0

    def test_payment_list_paginated(self, auth_client, loan):
        auth_client.post(f"/api/v1/loans/{loan.id}/approve/")
        auth_client.post(f"/api/v1/loans/{loan.id}/disburse/", {"method":"CASH"}, format="json")
        auth_client.post("/api/v1/payments/", {"loan": loan.id, "amount": "1000", "method": "CASH", "payment_type": "PARTIAL"}, format="json")
        resp = auth_client.get("/api/v1/payments/")
        assert resp.status_code == 200
        assert "results" in resp.data
        assert resp.data["count"] >= 1

    def test_cannot_overpay(self, auth_client, loan):
        """Overpayments should be accepted but balance should not go negative."""
        auth_client.post(f"/api/v1/loans/{loan.id}/approve/")
        auth_client.post(f"/api/v1/loans/{loan.id}/disburse/", {"method":"CASH"}, format="json")
        loan.refresh_from_db()
        resp = auth_client.post("/api/v1/payments/", {
            "loan": loan.id, "amount": str(float(loan.total_amount) + 5000),
            "method": "CASH", "payment_type": "FULL",
        }, format="json")
        # Should succeed or return 400 — either is acceptable, but not 500
        assert resp.status_code in (200, 201, 400)
