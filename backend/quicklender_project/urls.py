"""QuickLender Root URL Configuration"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import HttpResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.accounts.health import HealthCheckView
import os

# ── Serve frontend static files ───────────────────────────────────────────────
from django.views.static import serve as _static_serve

FRONTEND_DIR = settings.BASE_DIR.parent / 'frontend'  # BASE_DIR=backend/, parent=quicklender/

def serve_frontend(request, path):
    """Serve frontend HTML/CSS/JS from the frontend/ directory."""
    full_path = FRONTEND_DIR / path
    # Prevent directory traversal
    if not str(full_path.resolve()).startswith(str(FRONTEND_DIR.resolve())):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    if full_path.is_file():
        import mimetypes
        mime, _ = mimetypes.guess_type(str(full_path))
        mime = mime or 'application/octet-stream'
        with open(full_path, 'rb') as f:
            return HttpResponse(f.read(), content_type=mime)
    from django.http import Http404
    raise Http404(f"Frontend file not found: {path}")

urlpatterns = [
    # ── Root → login page ─────────────────────────────────────────────────────
    path('', RedirectView.as_view(url='/pages/login/login.html'), name='home'),

    # ── Frontend pages + assets ───────────────────────────────────────────────
    re_path(r'^pages/(?P<path>.+)$', lambda req, path: serve_frontend(req, 'pages/' + path)),
    re_path(r'^assets/(?P<path>.+)$',
            lambda req, path: serve_frontend(req, 'assets/' + path)),
    re_path(r'^components/(?P<path>.+)$',
            lambda req, path: serve_frontend(req, 'components/' + path)),

    # ── Diagnostic test page ──────────────────────────────────────────────────────
    path('test-connection.html', lambda req: serve_frontend(req, 'test-connection.html'),
         name='test-connection'),

    # ── Favicon (suppress 404 noise) ──────────────────────────────────────────
    path('favicon.ico', lambda req: HttpResponse(status=204)),

    # ── Django admin ──────────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── API v1 ────────────────────────────────────────────────────────────────
    path('api/v1/auth/',          include('apps.accounts.urls')),
    path('api/v1/customers/',     include('apps.customers.urls')),
    path('api/v1/loans/',         include('apps.loans.urls')),
    path('api/v1/payments/',      include('apps.payments.urls')),
    path('api/v1/branches/',      include('apps.branches.urls')),
    path('api/v1/reports/',       include('apps.reports.urls')),
    path('api/v1/allocations/',   include('apps.allocations.urls')),
    path('api/v1/assets/',        include('apps.assets.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/accounting/',    include('apps.accounting.urls')),
    path('api/v1/documents/',     include('apps.documents.urls')),
    path('api/v1/groups/',        include('apps.groups.urls')),
    path('api/v1/crm/',           include('apps.crm.urls')),

    # ── Health + API Docs ─────────────────────────────────────────────────────
    path('health/', HealthCheckView.as_view(), name='health'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/',   SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
