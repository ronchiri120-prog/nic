from django.urls import path
from .views import (
    CreditScoreView,
    LoanRestructureView,
    LoanExportView,
    LoanProductListCreateView, LoanProductDetailView, LoanListCreateView, LoanDetailView,
    LoanVerifyView, LoanApproveView, LoanRejectView, LoanDisburseView, LoanMarkDefaultView,
)

urlpatterns = [
    path('products/',              LoanProductListCreateView.as_view(), name='loan-products'),
    path('products/<int:pk>/',     LoanProductDetailView.as_view(),     name='loan-product-detail'),
    path('',                       LoanListCreateView.as_view(),        name='loan-list'),
    path('<int:pk>/',              LoanDetailView.as_view(),            name='loan-detail'),
    path('<int:pk>/verify/',       LoanVerifyView.as_view(),           name='loan-verify'),
    path('<int:pk>/approve/',      LoanApproveView.as_view(),           name='loan-approve'),
    path('<int:pk>/reject/',       LoanRejectView.as_view(),            name='loan-reject'),
    path('<int:pk>/disburse/',     LoanDisburseView.as_view(),          name='loan-disburse'),
    path('<int:pk>/mark-default/', LoanMarkDefaultView.as_view(),       name='loan-default'),
    path('credit-score/',          CreditScoreView.as_view(),          name='credit-score'),
    path('<int:pk>/restructure/',   LoanRestructureView.as_view(),      name='loan-restructure'),
    path('export/',                LoanExportView.as_view(),           name='loan-export'),
]
