"""Tests: Loan lifecycle"""
import pytest
from decimal import Decimal


@pytest.mark.django_db
class TestLoanCRUD:
    def test_create_loan(self, auth_client, customer, loan_product, branch):
        resp = auth_client.post('/api/v1/loans/', {
            'customer': customer.id,
            'product':  loan_product.id,
            'branch':   branch.id,
            'principal': '50000',
            'interest_rate': '10',
            'tenure_days': 30,
            'disbursement_method': 'MPESA',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['status'] == 'PENDING'
        assert resp.data['loan_id'].startswith('QL-L')
        assert Decimal(resp.data['total_amount']) == Decimal('55000')

    def test_loan_auto_calculates_interest(self, auth_client, customer, loan_product, branch):
        resp = auth_client.post('/api/v1/loans/', {
            'customer': customer.id,
            'product':  loan_product.id,
            'branch':   branch.id,
            'principal': '100000',
            'interest_rate': '15',
            'tenure_days': 30,
        }, format='json')
        assert resp.status_code == 201
        assert Decimal(resp.data['interest_amount']) == Decimal('15000')
        assert Decimal(resp.data['total_amount'])    == Decimal('115000')
        assert Decimal(resp.data['balance'])         == Decimal('115000')

    def test_approve_loan(self, auth_client, loan):
        resp = auth_client.post(f'/api/v1/loans/{loan.id}/approve/')
        assert resp.status_code == 200
        assert 'approved' in resp.data['detail'].lower()

        # Verify status changed
        loan.refresh_from_db()
        assert loan.status == 'APPROVED'

    def test_reject_loan(self, auth_client, loan):
        resp = auth_client.post(f'/api/v1/loans/{loan.id}/reject/', {
            'reason': 'Insufficient income documentation',
        }, format='json')
        assert resp.status_code == 200
        loan.refresh_from_db()
        assert loan.status == 'REJECTED'
        assert 'Insufficient income' in loan.rejection_reason

    def test_disburse_approved_loan(self, auth_client, loan):
        # Approve first
        auth_client.post(f'/api/v1/loans/{loan.id}/approve/')
        # Disburse
        resp = auth_client.post(f'/api/v1/loans/{loan.id}/disburse/', {
            'method': 'MPESA',
        }, format='json')
        assert resp.status_code == 200
        loan.refresh_from_db()
        assert loan.status == 'ACTIVE'
        assert loan.disbursed_at is not None
        assert loan.due_date is not None

    def test_cannot_disburse_pending_loan(self, auth_client, loan):
        resp = auth_client.post(f'/api/v1/loans/{loan.id}/disburse/', {
            'method': 'CASH'
        }, format='json')
        assert resp.status_code == 404  # Not found (wrong status)

    def test_list_loans_paginated(self, auth_client, loan):
        resp = auth_client.get('/api/v1/loans/')
        assert resp.status_code == 200
        assert 'results' in resp.data
        assert 'count' in resp.data


@pytest.mark.django_db
class TestPayments:
    def test_record_payment(self, auth_client, loan):
        from django.utils import timezone
        # Disburse loan first
        auth_client.post(f'/api/v1/loans/{loan.id}/approve/')
        auth_client.post(f'/api/v1/loans/{loan.id}/disburse/', {'method': 'CASH'}, format='json')

        resp = auth_client.post('/api/v1/payments/', {
            'loan':         loan.id,
            'amount':       '25000',
            'method':       'MPESA',
            'payment_type': 'PARTIAL',
            'mpesa_ref':    'QGJ72H4K2L',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['ref'].startswith('PMT-')

        # Check loan balance updated
        loan.refresh_from_db()
        assert loan.total_paid == Decimal('25000')

    def test_full_payment_closes_loan(self, auth_client, loan):
        auth_client.post(f'/api/v1/loans/{loan.id}/approve/')
        auth_client.post(f'/api/v1/loans/{loan.id}/disburse/', {'method': 'CASH'}, format='json')
        loan.refresh_from_db()

        auth_client.post('/api/v1/payments/', {
            'loan': loan.id,
            'amount': str(loan.total_amount),
            'method': 'CASH',
            'payment_type': 'FULL',
        }, format='json')

        loan.refresh_from_db()
        assert loan.status == 'CLOSED'
        assert loan.balance <= Decimal('0')
