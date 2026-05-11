"""Tests: SMS & Email notifications"""
import pytest


@pytest.mark.django_db
class TestSMSNotifications:
    def test_sms_log_created_on_send(self, db, customer, loan):
        from apps.notifications.sms import send_sms
        from apps.notifications.models import SMSLog
        initial_count = SMSLog.objects.count()
        result = send_sms("0712345678", "Test message from QuickLender", customer=customer)
        assert result["success"] is True
        assert SMSLog.objects.count() == initial_count + 1

    def test_dev_mode_sms_does_not_call_at(self, db, customer):
        """Without AT_API_KEY, SMS should succeed in dev mode."""
        from apps.notifications.sms import send_sms
        result = send_sms("0712345678", "Dev mode test")
        assert result["success"] is True
        assert result.get("dev_mode") is True

    def test_sms_log_list_endpoint(self, auth_client):
        resp = auth_client.get("/api/v1/notifications/sms/")
        assert resp.status_code == 200
        assert "results" in resp.data

    def test_notification_stats_endpoint(self, auth_client):
        resp = auth_client.get("/api/v1/notifications/stats/")
        assert resp.status_code == 200
        assert "sms" in resp.data
        assert "sms_total_today" in resp.data

    def test_manual_sms_send(self, auth_client):
        resp = auth_client.post("/api/v1/notifications/sms/send/", {
            "phone": "0712345678",
            "message": "Test manual SMS from QuickLender test suite",
        }, format="json")
        assert resp.status_code == 200
        assert resp.data.get("success") is True


@pytest.mark.django_db
class TestEmailNotifications:
    def test_email_log_created(self, db):
        from apps.notifications.email_service import send_email
        from apps.notifications.models import EmailLog
        count_before = EmailLog.objects.count()
        send_email("test@example.com", "Test Subject", "Test body")
        assert EmailLog.objects.count() == count_before + 1

    def test_email_log_endpoint(self, auth_client, admin_user):
        resp = auth_client.get("/api/v1/notifications/email/")
        assert resp.status_code == 200
