"""Tests: Customer management"""
import pytest


@pytest.mark.django_db
class TestCustomers:
    def test_create_customer(self, auth_client, branch, loan_officer):
        resp = auth_client.post('/api/v1/customers/', {
            'first_name':   'Alice',
            'last_name':    'Wanjiru',
            'national_id':  '99887766',
            'phone':        '0712345678',
            'branch':       branch.id,
            'loan_officer': loan_officer.id,
            'loan_limit':   100000,
            'monthly_income': 50000,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['uid'].startswith('QL-C')
        assert resp.data['status'] == 'ACTIVE'

    def test_customer_uid_unique(self, auth_client, branch, loan_officer):
        for i, nid in enumerate(['11111111', '22222222']):
            resp = auth_client.post('/api/v1/customers/', {
                'first_name': f'Customer{i}',
                'last_name':  'Test',
                'national_id': nid,
                'phone': '0712345678',
                'branch': branch.id,
                'loan_officer': loan_officer.id,
            }, format='json')
            assert resp.status_code == 201
        # Check UIDs differ
        all_uids = auth_client.get('/api/v1/customers/').data['results']
        uid_set = {c['uid'] for c in all_uids}
        assert len(uid_set) == len(all_uids)

    def test_blacklist_customer(self, auth_client, customer):
        resp = auth_client.post(f'/api/v1/customers/{customer.id}/blacklist/', {
            'reason': 'Multiple defaults on previous loans',
        }, format='json')
        assert resp.status_code == 200
        customer.refresh_from_db()
        assert customer.status == 'BLACKLISTED'

    def test_customer_loan_history(self, auth_client, customer, loan):
        resp = auth_client.get(f'/api/v1/customers/{customer.id}/loan-history/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1
        assert resp.data[0]['loan_id'] == loan.loan_id


@pytest.mark.django_db
class TestSMS:
    def test_normalize_phone(self):
        from apps.notifications.sms import normalize_phone
        assert normalize_phone('0712345678')  == '254712345678'
        assert normalize_phone('+254712345678')== '254712345678'
        assert normalize_phone('254712345678') == '254712345678'
        assert normalize_phone('0112345678')  == '254112345678'
        assert normalize_phone('invalid')     is None

    def test_render_template(self):
        from apps.notifications.sms import render_template
        msg = render_template('DISBURSEMENT', {
            'name': 'Alice', 'amount': '50,000', 'loan_id': 'QL-L001',
            'phone': '0712345678', 'total': '55,000', 'due_date': '01 Apr 2026',
            'shortcode': '174379',
        })
        assert 'Alice' in msg
        assert 'QL-L001' in msg
        assert '50,000' in msg

    def test_send_sms_dev_mode(self, db, customer, loan):
        from apps.notifications.sms import send_sms
        result = send_sms('0712345678', 'Test message', customer=customer, loan=loan)
        assert result['success'] is True
        assert result.get('dev_mode') is True  # No AT key configured in test
