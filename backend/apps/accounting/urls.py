from django.urls import path
from .views import (
    AccountListView, AccountDetailView,
    JournalEntryListCreateView, JournalEntryDetailView,
    PostJournalEntryView, ReverseJournalEntryView,
    IncomeStatementView, BalanceSheetView,
    TrialBalanceView, GeneralLedgerView,
    FiscalPeriodListCreateView, CloseFiscalPeriodView,
)

urlpatterns = [
    path("accounts/",                     AccountListView.as_view(),          name="gl-accounts"),
    path("accounts/<int:pk>/",            AccountDetailView.as_view(),         name="gl-account-detail"),
    path("journal/",                      JournalEntryListCreateView.as_view(),name="journal-list"),
    path("journal/<int:pk>/",             JournalEntryDetailView.as_view(),    name="journal-detail"),
    path("journal/<int:pk>/post/",        PostJournalEntryView.as_view(),      name="journal-post"),
    path("journal/<int:pk>/reverse/",     ReverseJournalEntryView.as_view(),   name="journal-reverse"),
    path("reports/income-statement/",     IncomeStatementView.as_view(),       name="report-pl"),
    path("reports/balance-sheet/",        BalanceSheetView.as_view(),          name="report-bs"),
    path("reports/trial-balance/",        TrialBalanceView.as_view(),          name="report-tb"),
    path("reports/general-ledger/",       GeneralLedgerView.as_view(),         name="report-gl"),
    path("periods/",                      FiscalPeriodListCreateView.as_view(),name="fiscal-periods"),
    path("periods/<int:pk>/close/",       CloseFiscalPeriodView.as_view(),     name="period-close"),
]
