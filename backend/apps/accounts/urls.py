"""accounts/urls.py"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    PasswordResetRequestView, PasswordResetConfirmView,
    TOTPSetupView, TOTPConfirmView, TOTPDisableView, TOTPVerifyView,
    LoginView, LogoutView, MeView, AvatarUploadView,
    UserListCreateView, UserDetailView,
    ChangePasswordView, AuditLogListView,
    DashboardStatsView,
)

urlpatterns = [
    path('login/',           LoginView.as_view(),            name='auth-login'),
    path('logout/',          LogoutView.as_view(),           name='auth-logout'),
    path('token/refresh/',   TokenRefreshView.as_view(),     name='token-refresh'),
    path('me/',              MeView.as_view(),               name='auth-me'),
    path('me/avatar/',       AvatarUploadView.as_view(),     name='avatar-upload'),
    path('users/',           UserListCreateView.as_view(),   name='user-list'),
    path('users/<int:pk>/',  UserDetailView.as_view(),       name='user-detail'),
    path('change-password/', ChangePasswordView.as_view(),   name='change-password'),
    path('audit-logs/',      AuditLogListView.as_view(),     name='audit-logs'),
    path('dashboard/stats/', DashboardStatsView.as_view(),   name='dashboard-stats'),
    path('password-reset/',         PasswordResetRequestView.as_view(),  name='password-reset'),
    path('password-reset/confirm/',  PasswordResetConfirmView.as_view(),  name='password-reset-confirm'),
    path('totp/setup/',    TOTPSetupView.as_view(),   name='totp-setup'),
    path('totp/confirm/',  TOTPConfirmView.as_view(), name='totp-confirm'),
    path('totp/disable/',  TOTPDisableView.as_view(), name='totp-disable'),
    path('totp/verify/',   TOTPVerifyView.as_view(),  name='totp-verify'),
]
