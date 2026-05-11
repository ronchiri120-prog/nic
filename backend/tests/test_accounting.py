"""Tests: Accounting GL, journal entries, financial reports"""
import pytest
from decimal import Decimal
from django.utils import timezone


@pytest.fixture
def chart_of_accounts(db):
    from django.core.management import call_command
    call_command("seed_chart_of_accounts", verbosity=0)


@pytest.mark.django_db
class TestGL:
    def test_post_loan_disbursement(self, chart_of_accounts, loan, admin_user):
        from apps.accounting.gl_service import post_loan_disbursement
        from apps.accounting.models import JournalEntry

        loan.status = "ACTIVE"
        loan.disbursement_method = "MPESA"
        loan.save()

        entry = post_loan_disbursement(loan, user=admin_user)
        assert entry is not None
        assert entry.status == "POSTED"
        assert entry.is_balanced
        assert entry.lines.count() == 2

    def test_payment_creates_gl_entry(self, chart_of_accounts, loan, admin_user):
        from apps.accounting.gl_service import post_loan_disbursement, post_interest_accrual, post_payment_received
        from apps.payments.models import Payment

        loan.status = "ACTIVE"
        loan.disbursement_method = "CASH"
        loan.save()
        post_loan_disbursement(loan)
        post_interest_accrual(loan)

        payment = Payment.objects.create(
            loan=loan, amount=Decimal("5000"), method="CASH",
            payment_type="PARTIAL", paid_at=timezone.now(),
        )
        entry = post_payment_received(payment, user=admin_user)
        assert entry is not None
        assert entry.status == "POSTED"
        assert entry.is_balanced

    def test_trial_balance_balanced(self, chart_of_accounts, auth_client):
        resp = auth_client.get("/api/v1/accounting/reports/trial-balance/")
        assert resp.status_code == 200
        assert resp.data["balanced"] is True

    def test_income_statement(self, chart_of_accounts, auth_client):
        today = timezone.now().date()
        resp = auth_client.get("/api/v1/accounting/reports/income-statement/", {
            "from": str(today.replace(day=1)),
            "to":   str(today),
        })
        assert resp.status_code == 200
        assert "income" in resp.data
        assert "expenses" in resp.data
        assert "net_profit" in resp.data

    def test_journal_entry_must_balance(self, chart_of_accounts, auth_client):
        resp = auth_client.post("/api/v1/accounting/journal/", {
            "narration": "Test imbalanced entry",
            "date": str(timezone.now().date()),
            "lines": [
                {"account": 1, "debit_amount": "10000", "credit_amount": "0"},
                {"account": 2, "debit_amount": "0",     "credit_amount": "5000"},  # Doesn't balance
            ],
            "post": True,
        }, format="json")
        # Should either reject or save as draft but not post
        if resp.status_code == 201:
            entry_id = resp.data["id"]
            post_resp = auth_client.post(f"/api/v1/accounting/journal/{entry_id}/post/")
            assert post_resp.status_code == 400  # Should fail — not balanced
