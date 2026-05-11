from django.urls import path
from .views import (
    LeadListCreateView, LeadDetailView, LeadConvertView,
    CustomerTierView,
    CustomerListCreateView, CustomerDetailView,
    CustomerBlacklistView, CustomerLoanHistoryView,
    CustomerExportView, CustomerBulkImportView,
    KYCUploadURLView, KYCDocumentListView, KYCDocumentConfirmView,
    CustomerReferenceView,
)

urlpatterns = [
    # Core CRUD
    path('',                              CustomerListCreateView.as_view(), name='customer-list'),
    path('<int:pk>/',                     CustomerDetailView.as_view(),     name='customer-detail'),
    path('<int:pk>/blacklist/',           CustomerBlacklistView.as_view(),  name='customer-blacklist'),
    path('<int:pk>/loan-history/',        CustomerLoanHistoryView.as_view(),name='customer-loans'),

    # Reference check (cross-branch duplicate prevention)
    path('reference/',                    CustomerReferenceView.as_view(),  name='customer-reference'),

    # Bulk import / export
    path('export/',                       CustomerExportView.as_view(),     name='customer-export'),
    # Leads
    path('leads/',                        LeadListCreateView.as_view(), name='lead-list'),
    path('leads/<int:pk>/',               LeadDetailView.as_view(),     name='lead-detail'),
    path('leads/<int:pk>/convert/',       LeadConvertView.as_view(),    name='lead-convert'),

    path('bulk-import/',                  CustomerBulkImportView.as_view(), name='customer-bulk-import'),

    # KYC document management
    path('<int:pk>/tier/',         CustomerTierView.as_view(),       name='customer-tier'),
    path('<int:pk>/kyc/',                 KYCDocumentListView.as_view(),    name='kyc-list'),
    path('<int:pk>/kyc/upload-url/',      KYCUploadURLView.as_view(),       name='kyc-upload-url'),
    path('<int:pk>/kyc/confirm/',         KYCDocumentConfirmView.as_view(), name='kyc-confirm'),
]
