"""
Health check HTTP view — mounted at /health/
Returns 200 if all systems operational, 503 if degraded.
"""
import json
import time
from django.http import JsonResponse
from django.views import View
from django.conf import settings


class HealthCheckView(View):
    """
    GET /health/  → {"status":"ok", "checks":{...}}
    GET /health/ready/ → 200 if ready, 503 if not
    """
    authentication_classes = []
    permission_classes      = []

    def get(self, request, check_type='liveness'):
        start = time.time()
        checks = {}

        # Database
        try:
            from django.db import connection
            with connection.cursor() as c:
                c.execute("SELECT 1")
            checks['database'] = {'status': 'ok'}
        except Exception as e:
            checks['database'] = {'status': 'error', 'detail': str(e)}

        # Redis
        try:
            import redis
            r = redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
            r.ping()
            checks['redis'] = {'status': 'ok'}
        except Exception as e:
            checks['redis'] = {'status': 'error', 'detail': str(e)}

        # Overall status
        all_ok = all(v['status'] == 'ok' for v in checks.values())
        status_code = 200 if all_ok else 503

        return JsonResponse({
            'status':    'ok' if all_ok else 'degraded',
            'service':   'quicklender-api',
            'version':   '3.0.0',
            'checks':    checks,
            'latency_ms': round((time.time() - start) * 1000, 1),
        }, status=status_code)
