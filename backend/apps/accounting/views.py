"""accounting/views.py — GL, reports, journal entry endpoints."""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
import datetime

from apps.accounts.permissions import IsAccountantOrAbove, IsBranchManagerOrAbove
from .models import Account, JournalEntry, FiscalPeriod
from .serializers import (
    AccountSerializer, JournalEntrySerializer,
    JournalEntryCreateSerializer, FiscalPeriodSerializer,
)
from . import reports


# ─── Chart of Accounts ────────────────────────────────────────────────────────
class AccountListView(generics.ListAPIView):
    serializer_class  = AccountSerializer
    permission_classes = [IsBranchManagerOrAbove]
    queryset = Account.objects.select_related("parent").filter(is_active=True)
    search_fields  = ["code","name"]
    filterset_fields = ["account_type","is_control"]


class AccountDetailView(generics.RetrieveAPIView):
    serializer_class  = AccountSerializer
    permission_classes = [IsAccountantOrAbove]
    queryset = Account.objects.all()


# ─── Journal Entries ──────────────────────────────────────────────────────────
class JournalEntryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAccountantOrAbove]
    search_fields  = ["reference","narration","source_type"]
    filterset_fields = ["status","source_type"]

    def get_serializer_class(self):
        return JournalEntryCreateSerializer if self.request.method == "POST" else JournalEntrySerializer

    def get_queryset(self):
        return JournalEntry.objects.prefetch_related("lines__account","lines__branch").order_by("-date","-created_at")

    def perform_create(self, serializer):
        entry = serializer.save(created_by=self.request.user)
        if self.request.data.get("post", False):
            entry.post(user=self.request.user)


class JournalEntryDetailView(generics.RetrieveAPIView):
    serializer_class  = JournalEntrySerializer
    permission_classes = [IsAccountantOrAbove]
    queryset = JournalEntry.objects.prefetch_related("lines__account")


class PostJournalEntryView(APIView):
    permission_classes = [IsAccountantOrAbove]

    def post(self, request, pk):
        try:
            entry = JournalEntry.objects.get(pk=pk, status="DRAFT")
            entry.post(user=request.user)
            return Response({"detail": f"{entry.reference} posted successfully."})
        except JournalEntry.DoesNotExist:
            return Response({"detail": "Entry not found or already posted."}, status=404)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)


class ReverseJournalEntryView(APIView):
    permission_classes = [IsAccountantOrAbove]

    def post(self, request, pk):
        try:
            entry = JournalEntry.objects.get(pk=pk, status="POSTED")
            rev = entry.reverse(user=request.user, narration=request.data.get("narration",""))
            return Response({"detail": f"Reversal {rev.reference} created.", "reversal_ref": rev.reference})
        except JournalEntry.DoesNotExist:
            return Response({"detail": "Entry not found or not posted."}, status=404)


# ─── Financial Reports ────────────────────────────────────────────────────────
class IncomeStatementView(APIView):
    permission_classes = [IsAccountantOrAbove]

    def get(self, request):
        today  = timezone.now().date()
        d_from = request.query_params.get("from", str(today.replace(day=1)))
        d_to   = request.query_params.get("to",   str(today))
        branch = request.query_params.get("branch")
        try:
            branch_obj = None
            if branch:
                from apps.branches.models import Branch
                branch_obj = Branch.objects.get(pk=branch)
            result = reports.income_statement(
                datetime.date.fromisoformat(d_from),
                datetime.date.fromisoformat(d_to),
                branch=branch_obj,
            )
            return Response(result)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class BalanceSheetView(APIView):
    permission_classes = [IsAccountantOrAbove]

    def get(self, request):
        as_at = request.query_params.get("as_at", str(timezone.now().date()))
        try:
            result = reports.balance_sheet(datetime.date.fromisoformat(as_at))
            return Response(result)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class TrialBalanceView(APIView):
    permission_classes = [IsAccountantOrAbove]

    def get(self, request):
        as_at = request.query_params.get("as_at", str(timezone.now().date()))
        try:
            result = reports.trial_balance(datetime.date.fromisoformat(as_at))
            return Response(result)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class GeneralLedgerView(APIView):
    permission_classes = [IsAccountantOrAbove]

    def get(self, request):
        code   = request.query_params.get("account")
        d_from = request.query_params.get("from")
        d_to   = request.query_params.get("to")
        if not code:
            return Response({"detail": "account code is required."}, status=400)
        try:
            result = reports.general_ledger(
                code,
                datetime.date.fromisoformat(d_from) if d_from else None,
                datetime.date.fromisoformat(d_to)   if d_to   else None,
            )
            return Response(result)
        except Account.DoesNotExist:
            return Response({"detail": f"Account {code} not found."}, status=404)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


# ─── Fiscal Periods ───────────────────────────────────────────────────────────
class FiscalPeriodListCreateView(generics.ListCreateAPIView):
    serializer_class  = FiscalPeriodSerializer
    permission_classes = [IsAccountantOrAbove]
    queryset = FiscalPeriod.objects.all()


class CloseFiscalPeriodView(APIView):
    permission_classes = [IsAccountantOrAbove]

    def post(self, request, pk):
        try:
            period = FiscalPeriod.objects.get(pk=pk, status="OPEN")
            period.status    = FiscalPeriod.Status.CLOSED
            period.closed_by = request.user
            period.closed_at = timezone.now()
            period.save()
            return Response({"detail": f"Period {period.name} closed."})
        except FiscalPeriod.DoesNotExist:
            return Response({"detail": "Period not found or already closed."}, status=404)
