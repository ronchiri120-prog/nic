from django.urls import path
from .views import (
    LoanGroupListCreateView, LoanGroupDetailView, AddGroupMemberView,
    GroupLoanListCreateView, ApproveGroupLoanView, DisburseGroupLoanView,
)

urlpatterns = [
    path("",                         LoanGroupListCreateView.as_view(), name="group-list"),
    path("<int:pk>/",                LoanGroupDetailView.as_view(),     name="group-detail"),
    path("<int:pk>/members/",        AddGroupMemberView.as_view(),      name="group-add-member"),
    path("loans/",                   GroupLoanListCreateView.as_view(), name="group-loan-list"),
    path("loans/<int:pk>/approve/",  ApproveGroupLoanView.as_view(),    name="group-loan-approve"),
    path("loans/<int:pk>/disburse/", DisburseGroupLoanView.as_view(),   name="group-loan-disburse"),
]
