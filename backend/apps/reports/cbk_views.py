"""reports/cbk_views.py — CBK regulatory report endpoints."""
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
import datetime
from apps.accounts.permissions import IsAccountantOrAbove
from .cbk_reporting import mfi_01_balance_sheet, mfi_02_income_statement, mfi_03_portfolio_quality, mfi_04_capital_adequacy


class CBKBalanceSheetView(APIView):
    permission_classes = [IsAccountantOrAbove]
    def get(self, request):
        as_at = request.query_params.get("as_at", str(timezone.now().date()))
        return Response(mfi_01_balance_sheet(datetime.date.fromisoformat(as_at)))

class CBKIncomeStatementView(APIView):
    permission_classes = [IsAccountantOrAbove]
    def get(self, request):
        today = timezone.now().date()
        d_from = request.query_params.get("from", str(today.replace(day=1)))
        d_to   = request.query_params.get("to",   str(today))
        return Response(mfi_02_income_statement(
            datetime.date.fromisoformat(d_from), datetime.date.fromisoformat(d_to)))

class CBKPortfolioQualityView(APIView):
    permission_classes = [IsAccountantOrAbove]
    def get(self, request):
        as_at = request.query_params.get("as_at", str(timezone.now().date()))
        return Response(mfi_03_portfolio_quality(datetime.date.fromisoformat(as_at)))

class CBKCapitalAdequacyView(APIView):
    permission_classes = [IsAccountantOrAbove]
    def get(self, request):
        return Response(mfi_04_capital_adequacy())
