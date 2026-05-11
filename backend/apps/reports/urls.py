from django.urls import path
from .views import (
    AgingReportView, EODReconciliationView,
    LoanBreakdownReportView, BranchPerformanceReportView,
    IndividualPerformanceReportView, DefaultersReportView,
    DormantCustomersReportView,
)
from .views import ExcelLoanPortfolioView, ExcelCollectionsView, ExcelCustomersView
from .cbk_views import CBKBalanceSheetView, CBKIncomeStatementView, CBKPortfolioQualityView, CBKCapitalAdequacyView

urlpatterns = [
    path("loans-breakdown/",        LoanBreakdownReportView.as_view(),         name="report-loans"),
    path("branch-performance/",     BranchPerformanceReportView.as_view(),     name="report-branches"),
    path("individual-performance/", IndividualPerformanceReportView.as_view(), name="report-individual"),
    path("defaulters/",             DefaultersReportView.as_view(),            name="report-defaulters"),
    path("aging/",               AgingReportView.as_view(),          name="report-aging"),
    path("eod/",                 EODReconciliationView.as_view(),     name="report-eod"),
    path("dormant-customers/",      DormantCustomersReportView.as_view(),      name="report-dormant"),
    path("excel/loans/",        ExcelLoanPortfolioView.as_view(),   name="excel-loans"),
    path("excel/collections/",  ExcelCollectionsView.as_view(),     name="excel-collections"),
    path("excel/customers/",    ExcelCustomersView.as_view(),       name="excel-customers"),
    path("cbk/mfi-01/",             CBKBalanceSheetView.as_view(),             name="cbk-bs"),
    path("cbk/mfi-02/",             CBKIncomeStatementView.as_view(),          name="cbk-is"),
    path("cbk/mfi-03/",             CBKPortfolioQualityView.as_view(),         name="cbk-pq"),
    path("cbk/mfi-04/",             CBKCapitalAdequacyView.as_view(),          name="cbk-ca"),
]
