from django.urls import path
from .views import (
    SMSLogListView, EmailLogListView,
    SendSMSView, ResendSMSView, NotificationStatsView,
)

urlpatterns = [
    path("sms/",              SMSLogListView.as_view(),   name="sms-logs"),
    path("sms/send/",         SendSMSView.as_view(),      name="sms-send"),
    path("sms/<int:pk>/retry/",ResendSMSView.as_view(),   name="sms-retry"),
    path("email/",            EmailLogListView.as_view(),  name="email-logs"),
    path("stats/",            NotificationStatsView.as_view(), name="notif-stats"),
]
