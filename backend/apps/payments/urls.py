from django.urls import path
from .views import (
    MpesaTokenTestView, PaymentReversalView, PrivilegedPaymentUploadView, BulkPaymentUploadView,
    MpesaC2BCallbackView, MpesaC2BValidationView,
    PaymentListCreateView, PaymentDetailView,
    MpesaSTKPushView, MpesaCallbackView, MpesaTransactionListView,
)

urlpatterns = [
    path('',                         PaymentListCreateView.as_view(),  name='payment-list'),
    path('<int:pk>/',                PaymentDetailView.as_view(),      name='payment-detail'),
    path('mpesa/stk-push/',          MpesaSTKPushView.as_view(),       name='mpesa-stk'),
    path('mpesa/callback/<str:txn_type>/', MpesaCallbackView.as_view(), name='mpesa-callback'),
    path('<int:pk>/reverse/',  PaymentReversalView.as_view(), name='payment-reverse'),
    path('upload/',       PrivilegedPaymentUploadView.as_view(), name='payment-upload'),
    path('bulk-upload/',  BulkPaymentUploadView.as_view(),       name='payment-bulk-upload'),
    path('mpesa/c2b/',          MpesaC2BCallbackView.as_view(),   name='mpesa-c2b'),
    path('mpesa/c2b/validate/', MpesaC2BValidationView.as_view(), name='mpesa-c2b-validate'),
    path('mpesa/transactions/',      MpesaTransactionListView.as_view(), name='mpesa-txns'),
    path('mpesa/test-token/',         MpesaTokenTestView.as_view(),       name='mpesa-test'),
]
