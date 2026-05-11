from apps.accounts.permissions import IsAccountantOrAbove, IsBranchManagerOrAbove
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from apps.accounts.permissions import IsBranchManagerOrAbove
"""reports/views.py — Analytics & Reporting"""
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
import datetime


class LoanBreakdownReportView(APIView):
    def get(self, request):
        from apps.loans.models import Loan
        from apps.loans.serializers import LoanListSerializer
        branch_id  = request.query_params.get("branch")
        status     = request.query_params.get("status")
        date_from  = request.query_params.get("from")
        date_to    = request.query_params.get("to")
        qs = Loan.objects.select_related("customer", "branch", "loan_officer", "product")
        
        # Role-based filtering
        user = request.user
        branch_level_roles = ['BDO', 'IDC', 'LOAN_OFFICER']
        regional_level_roles = ['BRANCH_MANAGER', 'RM']
        
        if user.role in branch_level_roles and user.branch:
            qs = qs.filter(branch=user.branch)
        elif user.role in regional_level_roles and user.region:
            qs = qs.filter(branch__region=user.region)
        
        if branch_id: qs = qs.filter(branch_id=branch_id)
        if status:    qs = qs.filter(status=status)
        if date_from: qs = qs.filter(disbursed_at__date__gte=date_from)
        if date_to:   qs = qs.filter(disbursed_at__date__lte=date_to)
        return Response({
            "count": qs.count(),
            "totals": qs.aggregate(
                total_principal=Sum("principal"),
                total_repayable=Sum("total_amount"),
                total_paid=Sum("total_paid"),
                total_balance=Sum("balance"),
            ),
            "loans": LoanListSerializer(qs[:100], many=True).data,
        })


@method_decorator(cache_page(300), name='get')
class BranchPerformanceReportView(APIView):
    def get(self, request):
        from apps.branches.models import Branch
        from apps.loans.models import Loan
        from apps.payments.models import Payment
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Role-based filtering
        user = request.user
        branch_level_roles = ['BDO', 'IDC', 'LOAN_OFFICER']
        regional_level_roles = ['BRANCH_MANAGER', 'RM']
        
        if user.role in branch_level_roles and user.branch:
            branches = Branch.objects.filter(id=user.branch.id)
        elif user.role in regional_level_roles and user.region:
            branches = Branch.objects.filter(region=user.region)
        elif user.role == 'BRANCH_MANAGER' and user.branch:
            branches = Branch.objects.filter(id=user.branch.id)
        else:
            branches = Branch.objects.filter(is_active=True)
        
        data = []
        for b in branches:
            loans = Loan.objects.filter(branch=b)
            payments = Payment.objects.filter(loan__branch=b, paid_at__date__gte=month_start)
            total_due = loans.filter(status="ACTIVE").aggregate(s=Sum("balance"))["s"] or 0
            collected = payments.aggregate(s=Sum("amount"))["s"] or 0
            data.append({
                "branch": b.name,
                "branch_id": b.id,
                "target": float(b.disb_target),
                "disbursed": float(loans.filter(
                    disbursed_at__date__gte=month_start
                ).aggregate(s=Sum("principal"))["s"] or 0),
                "total_due": float(total_due),
                "collected": float(collected),
                "collection_rate": round((collected / total_due * 100) if total_due else 0, 1),
                "active_loans": loans.filter(status="ACTIVE").count(),
                "defaulted": loans.filter(status="DEFAULT").count(),
            })
        return Response(data)


class IndividualPerformanceReportView(APIView):
    def get(self, request):
        from apps.accounts.models import User
        from apps.loans.models import Loan
        from apps.payments.models import Payment
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Role-based filtering
        user = request.user
        branch_level_roles = ['BDO', 'IDC', 'LOAN_OFFICER']
        regional_level_roles = ['BRANCH_MANAGER', 'RM']
        
        officers = User.objects.filter(role__in=["LOAN_OFFICER", "IDC", "BDO"], is_active=True)
        
        if user.role in branch_level_roles and user.branch:
            officers = officers.filter(branch=user.branch)
        elif user.role in regional_level_roles and user.region:
            officers = officers.filter(branch__region=user.region)
        
        data = []
        for officer in officers:
            loans = Loan.objects.filter(loan_officer=officer)
            disbursed = loans.filter(disbursed_at__date__gte=month_start).aggregate(s=Sum("principal"))["s"] or 0
            disb_rate = (float(disbursed) / float(officer.disbursement_target) * 100) if officer.disbursement_target else 0
            active = loans.filter(status="ACTIVE")
            due = active.aggregate(s=Sum("balance"))["s"] or 0
            collected = Payment.objects.filter(loan__loan_officer=officer, paid_at__date__gte=month_start).aggregate(s=Sum("amount"))["s"] or 0
            data.append({
                "officer": officer.full_name,
                "role": officer.role,
                "branch": officer.branch.name if officer.branch else None,
                "disb_target": float(officer.disbursement_target),
                "total_disbursed": float(disbursed),
                "disb_rate": round(disb_rate, 1),
                "active_customers": active.values("customer").distinct().count(),
                "total_paid": float(collected),
                "total_balance": float(due),
                "collection_rate": round((float(collected) / float(due) * 100) if due else 0, 1),
                "total_loans": loans.count(),
            })
        return Response(data)


class DefaultersReportView(APIView):
    def get(self, request):
        from apps.loans.models import Loan
        from apps.loans.serializers import LoanListSerializer
        today = timezone.now().date()
        defaults = Loan.objects.filter(
            Q(status="DEFAULT") | Q(status="ACTIVE", due_date__lt=today)
        ).select_related("customer", "branch", "loan_officer")
        
        # Role-based filtering
        user = request.user
        branch_level_roles = ['BDO', 'IDC', 'LOAN_OFFICER']
        regional_level_roles = ['BRANCH_MANAGER', 'RM']
        
        if user.role in branch_level_roles and user.branch:
            defaults = defaults.filter(branch=user.branch)
        elif user.role in regional_level_roles and user.region:
            defaults = defaults.filter(branch__region=user.region)
        
        return Response({
            "count": defaults.count(),
            "total_at_risk": float(defaults.aggregate(s=Sum("balance"))["s"] or 0),
            "loans": LoanListSerializer(defaults, many=True).data,
        })


class DormantCustomersReportView(APIView):
    def get(self, request):
        from apps.customers.models import Customer
        from apps.customers.serializers import CustomerListSerializer
        dormant = Customer.objects.filter(status="DORMANT").select_related("branch", "loan_officer")
        
        # Role-based filtering
        user = request.user
        branch_level_roles = ['BDO', 'IDC', 'LOAN_OFFICER']
        regional_level_roles = ['BRANCH_MANAGER', 'RM']
        
        if user.role in branch_level_roles and user.branch:
            dormant = dormant.filter(branch=user.branch)
        elif user.role in regional_level_roles and user.region:
            dormant = dormant.filter(branch__region=user.region)
        
        return Response(CustomerListSerializer(dormant, many=True).data)


class ExcelLoanPortfolioView(APIView):
    """GET /api/v1/reports/excel/loans/ — Download loan portfolio as Excel."""
    permission_classes = [IsBranchManagerOrAbove]

    def get(self, request):
        from apps.reports.excel_export import export_loan_portfolio
        from apps.loans.models import Loan
        qs = Loan.objects.select_related('customer','product','branch','loan_officer')
        user = request.user
        if not user.is_superuser and user.role not in ('SUPER_ADMIN',):
            if hasattr(user, 'branch') and user.branch:
                qs = qs.filter(branch=user.branch)
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        return export_loan_portfolio(qs)


class ExcelCollectionsView(APIView):
    """GET /api/v1/reports/excel/collections/ — Download overdue loans as Excel."""
    permission_classes = [IsBranchManagerOrAbove]

    def get(self, request):
        from apps.reports.excel_export import export_collections_report
        return export_collections_report()


class ExcelCustomersView(APIView):
    """GET /api/v1/reports/excel/customers/ — Download customer registry as Excel."""
    permission_classes = [IsBranchManagerOrAbove]

    def get(self, request):
        from apps.reports.excel_export import export_customer_registry
        return export_customer_registry()


class AgingReportView(APIView):
    """
    GET /api/v1/reports/aging/
    Loan aging buckets: current, 1-30d, 31-60d, 61-90d, 90d+
    Essential CBK / MFI risk management report.
    """
    permission_classes = [IsBranchManagerOrAbove]

    def get(self, request):
        from apps.loans.models import Loan
        from django.db.models import Sum, Count
        from django.utils import timezone

        today = timezone.now().date()
        branch_id = request.query_params.get('branch')
        qs = Loan.objects.filter(status__in=['ACTIVE', 'DEFAULT'])
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        buckets = {
            'current':  {'label': 'Current (0 days)',   'min': None, 'max': 0,   'loans': [], 'principal': 0, 'balance': 0, 'count': 0},
            'b1_30':    {'label': '1 – 30 days',        'min': 1,    'max': 30,  'loans': [], 'principal': 0, 'balance': 0, 'count': 0},
            'b31_60':   {'label': '31 – 60 days',       'min': 31,   'max': 60,  'loans': [], 'principal': 0, 'balance': 0, 'count': 0},
            'b61_90':   {'label': '61 – 90 days',       'min': 61,   'max': 90,  'loans': [], 'principal': 0, 'balance': 0, 'count': 0},
            'b90_plus': {'label': '90+ days (NPL)',     'min': 91,   'max': None,'loans': [], 'principal': 0, 'balance': 0, 'count': 0},
        }

        total_portfolio = 0
        total_at_risk   = 0

        for loan in qs.select_related('customer', 'branch', 'loan_officer').iterator(chunk_size=500):
            due = loan.due_date
            bal = float(loan.balance or 0)
            pri = float(loan.principal or 0)
            total_portfolio += pri

            if not due or due >= today:
                days = 0
            else:
                days = (today - due).days

            # Assign to bucket
            for key, bucket in buckets.items():
                lo = bucket['min']
                hi = bucket['max']
                if (lo is None or days >= lo) and (hi is None or days <= hi):
                    bucket['count']     += 1
                    bucket['principal'] += pri
                    bucket['balance']   += bal
                    if days > 0:
                        total_at_risk += bal
                    break

        # Compute PAR ratios
        for bucket in buckets.values():
            bucket['par_ratio'] = (
                round(bucket['balance'] / total_portfolio * 100, 2)
                if total_portfolio > 0 else 0
            )
            bucket.pop('loans', None)

        par_30 = sum(buckets[k]['balance'] for k in ['b1_30', 'b31_60', 'b61_90', 'b90_plus'])
        par_90 = sum(buckets[k]['balance'] for k in ['b61_90', 'b90_plus'])

        return Response({
            'buckets':         buckets,
            'total_portfolio': round(total_portfolio, 2),
            'total_at_risk':   round(total_at_risk, 2),
            'par_30':          round(par_30, 2),
            'par_30_ratio':    round(par_30 / total_portfolio * 100, 2) if total_portfolio else 0,
            'par_90':          round(par_90, 2),
            'par_90_ratio':    round(par_90 / total_portfolio * 100, 2) if total_portfolio else 0,
            'generated_at':    str(today),
        })


class EODReconciliationView(APIView):
    """
    GET /api/v1/reports/eod/?date=YYYY-MM-DD
    End-of-day cash reconciliation: all payments received on a given date
    grouped by method, balanced against disbursements.
    """
    permission_classes = [IsAccountantOrAbove]

    def get(self, request):
        from apps.loans.models import Loan
        from apps.payments.models import Payment
        from django.db.models import Sum
        from django.utils import timezone
        import datetime

        date_str = request.query_params.get('date', str(timezone.now().date()))
        try:
            eod_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Invalid date. Use YYYY-MM-DD.'}, status=400)

        # Payments received
        payments = Payment.objects.filter(paid_at__date=eod_date)
        by_method = {}
        for p in payments.values('method').annotate(
            count=Count('id'), total=Sum('amount')
        ):
            by_method[p['method']] = {
                'count': p['count'],
                'total': float(p['total'] or 0),
            }

        total_received = float(payments.aggregate(t=Sum('amount'))['t'] or 0)

        # Disbursements
        disb = Loan.objects.filter(disbursed_at__date=eod_date, status__in=['ACTIVE','CLOSED'])
        total_disbursed = float(disb.aggregate(t=Sum('principal'))['t'] or 0)

        # Loans approved today
        approved_today = Loan.objects.filter(
            approved_at__date=eod_date
        ).count()

        return Response({
            'date':            str(eod_date),
            'payments': {
                'total_received': total_received,
                'by_method':      by_method,
                'count':          payments.count(),
            },
            'disbursements': {
                'total_disbursed': total_disbursed,
                'count':           disb.count(),
            },
            'approvals':     {'count': approved_today},
            'net_cash':      round(total_received - total_disbursed, 2),
        })
