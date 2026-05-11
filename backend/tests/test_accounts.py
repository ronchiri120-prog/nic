"""Tests: Accounts — users, roles, 2FA, audit logs"""
import pytest


@pytest.mark.django_db
class TestUserManagement:
    def test_list_users(self, auth_client, admin_user):
        resp = auth_client.get('/api/v1/auth/users/')
        assert resp.status_code == 200
        emails = [u['email'] for u in (resp.data.get('results') or resp.data)]
        assert admin_user.email in emails

    def test_create_user(self, auth_client, branch):
        resp = auth_client.post('/api/v1/auth/users/', {
            'email':     'new.officer@quicklender.co.ke',
            'full_name': 'New Officer',
            'role':      'LOAN_OFFICER',
            'branch':    branch.id,
            'password':  'TestPass@2026',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['role'] == 'LOAN_OFFICER'
        assert resp.data['staff_id'].startswith('STF-')

    def test_change_password(self, auth_client, admin_user):
        resp = auth_client.post('/api/v1/auth/change-password/', {
            'old_password': 'TestPass@2026',
            'new_password': 'NewTestPass@2026',
        }, format='json')
        assert resp.status_code == 200

    def test_audit_log_endpoint(self, auth_client):
        resp = auth_client.get('/api/v1/auth/audit-logs/')
        assert resp.status_code == 200
        assert 'results' in resp.data

    def test_dashboard_stats(self, auth_client):
        resp = auth_client.get('/api/v1/auth/dashboard/stats/')
        assert resp.status_code == 200
        required_keys = ['total_customers', 'active_loans', 'defaulted_loans',
                         'mtd_disbursements', 'mtd_collections', 'pending_applications']
        for k in required_keys:
            assert k in resp.data, f'Missing key: {k}'


@pytest.mark.django_db
class TestTOTP2FA:
    def test_totp_setup_returns_qr(self, auth_client, admin_user):
        resp = auth_client.get('/api/v1/auth/totp/setup/')
        assert resp.status_code == 200
        assert 'secret' in resp.data
        assert 'qr_code' in resp.data
        assert 'uri' in resp.data
        assert len(resp.data['secret']) >= 16

    def test_totp_setup_when_already_enabled(self, auth_client, admin_user):
        # Enable 2FA first
        admin_user.totp_enabled = True
        admin_user.totp_secret  = 'JBSWY3DPEHPK3PXP'
        admin_user.save()
        resp = auth_client.get('/api/v1/auth/totp/setup/')
        assert resp.status_code == 400

    def test_totp_confirm_wrong_token(self, auth_client, admin_user):
        # Setup first
        auth_client.get('/api/v1/auth/totp/setup/')
        resp = auth_client.post('/api/v1/auth/totp/confirm/', {
            'token': '000000'
        }, format='json')
        # Should fail with invalid token
        assert resp.status_code == 400

    def test_totp_confirm_valid_token(self, auth_client, admin_user):
        import pyotp
        # Generate a secret and set it
        secret = pyotp.random_base32()
        admin_user.totp_secret  = secret
        admin_user.totp_enabled = False
        admin_user.save()

        token = pyotp.TOTP(secret).now()
        resp  = auth_client.post('/api/v1/auth/totp/confirm/', {
            'token': token,
        }, format='json')
        assert resp.status_code == 200
        assert 'backup_codes' in resp.data
        assert len(resp.data['backup_codes']) == 10
        admin_user.refresh_from_db()
        assert admin_user.totp_enabled is True


@pytest.mark.django_db
class TestPermissions:
    def test_loan_officer_cannot_delete_user(self, api_client, db, branch):
        from apps.accounts.models import User
        lo = User.objects.create_user(
            email='lo@test.co.ke', password='pass', full_name='Loan Officer',
            role=User.Role.LOAN_OFFICER, branch=branch,
        )
        api_client.force_authenticate(user=lo)
        resp = api_client.delete(f'/api/v1/auth/users/{lo.id}/')
        assert resp.status_code in (403, 405)

    def test_unauthenticated_cannot_access_loans(self, api_client):
        resp = api_client.get('/api/v1/loans/')
        assert resp.status_code == 401

    def test_health_endpoint_requires_no_auth(self, api_client):
        resp = api_client.get('/health/')
        assert resp.status_code in (200, 503)
        assert 'status' in resp.data
