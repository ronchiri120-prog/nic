"""Tests: Authentication endpoints"""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client, admin_user):
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'admin@test.co.ke',
            'password': 'TestPass@2026',
        }, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh' in resp.data
        assert 'user' in resp.data
        assert resp.data['user']['role'] == 'SUPER_ADMIN'

    def test_login_wrong_password(self, api_client, admin_user):
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'admin@test.co.ke',
            'password': 'WrongPassword',
        }, format='json')
        assert resp.status_code == 401

    def test_login_invalid_email(self, api_client):
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'notexist@test.co.ke',
            'password': 'any',
        }, format='json')
        assert resp.status_code == 401

    def test_me_authenticated(self, auth_client, admin_user):
        resp = auth_client.get('/api/v1/auth/me/')
        assert resp.status_code == 200
        assert resp.data['email'] == admin_user.email
        assert resp.data['role'] == 'SUPER_ADMIN'

    def test_me_unauthenticated(self, api_client):
        resp = api_client.get('/api/v1/auth/me/')
        assert resp.status_code == 401

    def test_dashboard_stats(self, auth_client):
        resp = auth_client.get('/api/v1/auth/dashboard/stats/')
        assert resp.status_code == 200
        assert 'active_loans' in resp.data
        assert 'total_customers' in resp.data
        assert 'mtd_disbursements' in resp.data
