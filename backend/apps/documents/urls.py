from django.urls import path
from .views import (
    PaymentReceiptView,
    CustomerStatementView, LoanAgreementView,
    DisbursementLetterView, DemandLetterView,
    LoanScheduleView,
)

urlpatterns = [
    path('customers/<int:pk>/statement/',    CustomerStatementView.as_view(),  name='customer-statement'),
    path('loans/<int:pk>/agreement/',        LoanAgreementView.as_view(),      name='loan-agreement'),
    path('loans/<int:pk>/disbursement-letter/', DisbursementLetterView.as_view(), name='disbursement-letter'),
    path('loans/<int:pk>/demand-letter/',    DemandLetterView.as_view(),       name='demand-letter'),
    path('payments/<int:pk>/receipt/',  PaymentReceiptView.as_view(),   name='payment-receipt'),
    path('loans/<int:pk>/schedule/',         LoanScheduleView.as_view(),       name='loan-schedule'),
]
