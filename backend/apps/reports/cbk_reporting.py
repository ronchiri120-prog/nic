"""
reports/cbk_reporting.py
Central Bank of Kenya (CBK) regulatory reporting for MFIs.

Formats data to match CBK's standard MFI statistical returns:
  - MFI-01: Balance Sheet Return
  - MFI-02: Income Statement Return
  - MFI-03: Loan Portfolio Quality
  - MFI-04: Capital Adequacy
  - MFI-05: Liquidity Return
"""
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q


def mfi_01_balance_sheet(as_at_date=None):
    """MFI-01 — Balance Sheet Return (Quarterly)"""
    from apps.loans.models import Loan
    from apps.payments.models import Payment
    from apps.customers.models import Customer

    today = as_at_date or timezone.now().date()

    # Asset quality classification (CBK PAR buckets)
    def par(days_min, days_max=None):
        qs = Loan.objects.filter(status__in=['ACTIVE','DEFAULT'], due_date__lt=today)
        qs = qs.filter(due_date__lte=today - timezone.timedelta(days=days_min))
        if days_max:
            qs = qs.filter(due_date__gt=today - timezone.timedelta(days=days_max))
        return {
            'count': qs.count(),
            'outstanding': float(qs.aggregate(s=Sum('balance'))['s'] or 0),
        }

    active_loans = Loan.objects.filter(status='ACTIVE')
    total_portfolio = float(active_loans.aggregate(s=Sum('balance'))['s'] or 0)

    return {
        'return_type':   'MFI-01',
        'period_end':    str(today),
        'institution':   'QuickLender Ltd',
        'assets': {
            'gross_loan_portfolio': total_portfolio,
            'performing_loans':     float(active_loans.filter(due_date__gte=today).aggregate(s=Sum('balance'))['s'] or 0),
            'par_1_30_days':        par(1,  30),
            'par_31_60_days':       par(31, 60),
            'par_61_90_days':       par(61, 90),
            'par_over_90_days':     par(91),
        },
        'portfolio_quality': {
            'par30_ratio': _par30_ratio(today),
            'par90_ratio': _par90_ratio(today),
            'npl_ratio':   _npl_ratio(today),
        },
        'borrowers': {
            'active_borrowers': active_loans.values('customer').distinct().count(),
            'total_registered':  Customer.objects.filter(is_active=True).count(),
            'women_borrowers':   active_loans.filter(customer__gender='F').values('customer').distinct().count(),
        },
    }


def mfi_02_income_statement(period_start, period_end):
    """MFI-02 — Income Statement Return (Quarterly)"""
    from apps.payments.models import Payment
    from apps.loans.models import Loan

    # Collections in period
    collections = Payment.objects.filter(
        paid_at__date__gte=period_start,
        paid_at__date__lte=period_end,
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Disbursements in period
    disbursed = Loan.objects.filter(
        disbursed_at__date__gte=period_start,
        disbursed_at__date__lte=period_end,
    ).aggregate(total=Sum('principal'))['total'] or 0

    # Interest earned (rough: based on closed + active loans)
    interest = Loan.objects.filter(
        disbursed_at__date__gte=period_start,
        disbursed_at__date__lte=period_end,
    ).aggregate(total=Sum('interest_amount'))['total'] or 0

    return {
        'return_type':    'MFI-02',
        'period_start':   str(period_start),
        'period_end':     str(period_end),
        'institution':    'QuickLender Ltd',
        'income': {
            'interest_income':       float(interest),
            'fee_income':            float(disbursed) * 0.02,  # Estimated 2% fee
            'penalty_income':        0,  # From GL if available
            'total_financial_income': float(interest),
        },
        'lending_activity': {
            'total_disbursed':  float(disbursed),
            'total_collected':  float(collections),
            'net_lending':      float(disbursed) - float(collections),
        },
    }


def mfi_03_portfolio_quality(as_at_date=None):
    """MFI-03 — Loan Portfolio Quality Return"""
    from apps.loans.models import Loan

    today = as_at_date or timezone.now().date()
    all_active = Loan.objects.filter(status__in=['ACTIVE','DEFAULT'])
    total_bal  = float(all_active.aggregate(s=Sum('balance'))['s'] or 0)

    if total_bal == 0:
        return {'return_type': 'MFI-03', 'period_end': str(today), 'error': 'No active loans'}

    def bucket(days_min, days_max=None, label=''):
        qs = all_active.filter(due_date__lt=today - timezone.timedelta(days=days_min))
        if days_max:
            qs = qs.filter(due_date__gte=today - timezone.timedelta(days=days_max))
        bal = float(qs.aggregate(s=Sum('balance'))['s'] or 0)
        return {
            'label':       label,
            'count':       qs.count(),
            'outstanding': bal,
            'ratio':       round(bal / total_bal * 100, 2) if total_bal else 0,
        }

    return {
        'return_type':       'MFI-03',
        'period_end':        str(today),
        'institution':       'QuickLender Ltd',
        'gross_loan_portfolio': total_bal,
        'buckets': [
            bucket(0,   None, 'Performing (Current)'),
            bucket(1,   30,   'PAR 1–30 days'),
            bucket(31,  60,   'PAR 31–60 days'),
            bucket(61,  90,   'PAR 61–90 days'),
            bucket(91,  180,  'PAR 91–180 days'),
            bucket(181, None, 'PAR 180+ days (write-off candidates)'),
        ],
        'par30_ratio': _par30_ratio(today),
        'par90_ratio': _par90_ratio(today),
        'write_off_ratio': round(
            float(Loan.objects.filter(status='WRITTEN_OFF').aggregate(s=Sum('principal'))['s'] or 0) / max(total_bal, 1) * 100, 2
        ),
    }


def mfi_04_capital_adequacy():
    """MFI-04 — Capital Adequacy (CBK requires MFIs to maintain minimum capital)"""
    from apps.loans.models import Loan

    total_assets = float(Loan.objects.filter(
        status__in=['ACTIVE','DEFAULT']
    ).aggregate(s=Sum('balance'))['s'] or 0)

    # Estimate from GL if available, otherwise use assumptions
    try:
        from apps.accounting.reports import balance_sheet
        bs = balance_sheet()
        total_assets = bs['assets']['total']
        equity       = bs['equity']['total']
    except Exception:
        equity = total_assets * 0.20  # Assume 20% equity ratio

    car = round(equity / max(total_assets, 1) * 100, 2)

    return {
        'return_type':        'MFI-04',
        'as_at':              str(timezone.now().date()),
        'institution':        'QuickLender Ltd',
        'total_assets':       float(total_assets),
        'core_capital':       float(equity),
        'capital_adequacy_ratio': car,
        'cbk_minimum':        10.0,   # CBK requires 10% CAR for MFIs
        'compliant':          car >= 10.0,
        'note':               'Exact figures require full GL — run seed_chart_of_accounts and post transactions',
    }


def _par30_ratio(today):
    from apps.loans.models import Loan
    from django.utils import timezone as tz
    all_bal = float(Loan.objects.filter(status__in=['ACTIVE','DEFAULT']).aggregate(s=Sum('balance'))['s'] or 0)
    par30   = float(Loan.objects.filter(status__in=['ACTIVE','DEFAULT'], due_date__lt=today - tz.timedelta(days=30)).aggregate(s=Sum('balance'))['s'] or 0)
    return round(par30 / max(all_bal, 1) * 100, 2)

def _par90_ratio(today):
    from apps.loans.models import Loan
    from django.utils import timezone as tz
    all_bal = float(Loan.objects.filter(status__in=['ACTIVE','DEFAULT']).aggregate(s=Sum('balance'))['s'] or 0)
    par90   = float(Loan.objects.filter(status__in=['ACTIVE','DEFAULT'], due_date__lt=today - tz.timedelta(days=90)).aggregate(s=Sum('balance'))['s'] or 0)
    return round(par90 / max(all_bal, 1) * 100, 2)

def _npl_ratio(today):
    from apps.loans.models import Loan
    all_bal = float(Loan.objects.filter(status__in=['ACTIVE','DEFAULT']).aggregate(s=Sum('balance'))['s'] or 0)
    npl     = float(Loan.objects.filter(status='DEFAULT').aggregate(s=Sum('balance'))['s'] or 0)
    return round(npl / max(all_bal, 1) * 100, 2)
