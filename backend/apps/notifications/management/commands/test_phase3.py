"""
Management command: python manage.py test_phase3
Tests all Phase 3 integrations: SMS, email, M-Pesa, Celery.
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Tests Phase 3 integrations: SMS, Email, M-Pesa, Celery'

    def handle(self, *args, **options):
        self.stdout.write('\n⚡ QuickLender Phase 3 Integration Test\n' + '─'*50)

        self._test_sms()
        self._test_email()
        self._test_mpesa()
        self._test_celery()
        self._test_db()

        self.stdout.write('\n' + '─'*50)
        self.stdout.write(self.style.SUCCESS('Phase 3 test complete.'))

    def _test_sms(self):
        self.stdout.write('\n[SMS — Africa\'s Talking]')
        api_key = getattr(settings, 'AT_API_KEY', '')
        if not api_key or api_key == 'your_at_api_key_here':
            self.stdout.write(self.style.WARNING('  ⚠  AT_API_KEY not set — running in DEV mode (logs only)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✓  AT_API_KEY configured (username: {settings.AT_USERNAME})'))

        # Test phone normalisation
        from apps.notifications.sms import normalize_phone
        tests = [('0712345678','254712345678'), ('+254723456789','254723456789'), ('0112345678','254112345678')]
        for raw, expected in tests:
            result = normalize_phone(raw)
            if result == expected:
                self.stdout.write(f'  ✓  normalize_phone({raw}) → {result}')
            else:
                self.stdout.write(self.style.ERROR(f'  ✗  normalize_phone({raw}) → {result} (expected {expected})'))

        # Send a test SMS (DEV mode)
        from apps.notifications.sms import send_sms
        result = send_sms('0712345678', 'QuickLender Phase 3 test SMS. Ignore.')
        if result.get('success'):
            self.stdout.write(self.style.SUCCESS(f'  ✓  Test SMS sent ({result.get("message_id","")})'))
        else:
            self.stdout.write(self.style.ERROR(f'  ✗  Test SMS failed: {result.get("error")}'))

    def _test_email(self):
        self.stdout.write('\n[Email — Django Backend]')
        backend = getattr(settings, 'EMAIL_BACKEND', '')
        if 'console' in backend:
            self.stdout.write(self.style.WARNING('  ⚠  Using console backend — emails print to terminal'))
            self.stdout.write('     Set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend for live emails')
        elif 'smtp' in backend:
            host = getattr(settings, 'EMAIL_HOST', '')
            self.stdout.write(self.style.SUCCESS(f'  ✓  SMTP configured ({host}:{settings.EMAIL_PORT})'))
        else:
            self.stdout.write(f'  ℹ  Backend: {backend}')

        # Send a test email
        from apps.notifications.email_service import send_email
        result = send_email(
            recipient=getattr(settings, 'EMAIL_HOST_USER', 'test@example.com') or 'test@example.com',
            subject='QuickLender Phase 3 Test',
            body_text='This is a test email from QuickLender Phase 3 integration check.',
        )
        if result.get('success'):
            self.stdout.write(self.style.SUCCESS('  ✓  Test email sent successfully'))
        else:
            self.stdout.write(self.style.WARNING(f'  ⚠  Email: {result.get("error", "check console output")}'))

    def _test_mpesa(self):
        self.stdout.write('\n[M-Pesa — Safaricom Daraja]')
        key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        env = getattr(settings, 'MPESA_ENV', 'sandbox')
        if not key or key == 'your_consumer_key_here':
            self.stdout.write(self.style.WARNING(f'  ⚠  MPESA_CONSUMER_KEY not set — Daraja calls will fail'))
            self.stdout.write(f'     Get sandbox credentials: developer.safaricom.co.ke')
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✓  MPESA_CONSUMER_KEY configured ({env} environment)'))
            # Try to get access token
            try:
                from apps.payments.mpesa import get_access_token
                token = get_access_token()
                self.stdout.write(self.style.SUCCESS(f'  ✓  Daraja OAuth token obtained (len={len(token)})'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗  Daraja auth failed: {e}'))

        self.stdout.write(f'  ℹ  Shortcode: {getattr(settings,"MPESA_SHORTCODE","174379")} | Env: {env}')
        self.stdout.write(f'  ℹ  Callback: {getattr(settings,"MPESA_CALLBACK_URL","not set")}')

    def _test_celery(self):
        self.stdout.write('\n[Celery — Task Queue]')
        try:
            from celery_app import app
            inspect = app.control.inspect(timeout=1)
            active = inspect.active()
            if active:
                workers = list(active.keys())
                self.stdout.write(self.style.SUCCESS(f'  ✓  Celery workers online: {workers}'))
            else:
                self.stdout.write(self.style.WARNING('  ⚠  No Celery workers detected'))
                self.stdout.write('     Start: celery -A quicklender_project worker -l info -B')
        except Exception:
            # Celery not importable in this env — check broker
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            self.stdout.write(f'  ℹ  Broker URL: {redis_url}')
            self.stdout.write('     Start workers: celery -A quicklender_project worker -l info')
            self.stdout.write('     Start beat:    celery -A quicklender_project beat -l info')

        # Show scheduled tasks
        self.stdout.write('\n  Scheduled tasks:')
        beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        for name, config in beat_schedule.items():
            self.stdout.write(f'    • {name} → {config["task"]}')

    def _test_db(self):
        self.stdout.write('\n[Database — Notification Tables]')
        try:
            from apps.notifications.models import SMSLog, EmailLog
            sms_count   = SMSLog.objects.count()
            email_count = EmailLog.objects.count()
            self.stdout.write(self.style.SUCCESS(f'  ✓  ql_sms_logs: {sms_count} records'))
            self.stdout.write(self.style.SUCCESS(f'  ✓  ql_email_logs: {email_count} records'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗  DB error: {e} (run migrations first)'))
