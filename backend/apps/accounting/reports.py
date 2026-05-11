"""
accounting/reports.py
Financial statement generators: P&L, Balance Sheet, Trial Balance, Cash Flow.
All pull live from the GL — no hardcoded numbers.
"""
from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Account, AccountType, JournalLine


def _balance(code_prefix, date_from=None, date_to=None):
    """Sum all posted lines for accounts matching a code prefix."""
    qs = JournalLine.objects.filter(
        account__code__startswith=code_prefix,
        entry__status='POSTED',
    )
    if date_from:
        qs = qs.filter(entry__date__gte=date_from)
    if date_to:
        qs = qs.filter(entry__date__lte=date_to)
    agg = qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
    return (agg['d'] or Decimal('0')), (agg['c'] or Decimal('0'))


def _net(code_prefix, date_from=None, date_to=None, normal='debit'):
    """Net balance for a code prefix."""
    d, c = _balance(code_prefix, date_from, date_to)
    return d - c if normal == 'debit' else c - d


def income_statement(date_from, date_to, branch=None):
    """
    Profit & Loss Statement for a period.
    Returns structured dict ready for API or PDF rendering.
    """
    def period_net(prefix, normal='credit'):
        qs = JournalLine.objects.filter(
            account__code__startswith=prefix,
            entry__status='POSTED',
            entry__date__gte=date_from,
            entry__date__lte=date_to,
        )
        if branch:
            qs = qs.filter(branch=branch)
        agg = qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
        d = agg['d'] or Decimal('0')
        c = agg['c'] or Decimal('0')
        return c - d if normal == 'credit' else d - c

    # Income lines
    interest_income = period_net('4010')
    fee_income      = period_net('4020')
    penalty_income  = period_net('4030')
    total_income    = interest_income + fee_income + penalty_income

    # Expense lines
    staff_costs  = period_net('5010', 'debit')
    rent_util    = period_net('5020', 'debit')
    mpesa_costs  = period_net('5030', 'debit')
    loan_loss    = period_net('5040', 'debit')
    admin_exp    = period_net('5050', 'debit')
    total_expenses = staff_costs + rent_util + mpesa_costs + loan_loss + admin_exp

    net_profit = total_income - total_expenses

    return {
        'period': {'from': str(date_from), 'to': str(date_to)},
        'income': {
            'items': [
                {'name': 'Interest Income',  'amount': float(interest_income)},
                {'name': 'Fee Income',       'amount': float(fee_income)},
                {'name': 'Penalty Income',   'amount': float(penalty_income)},
            ],
            'total': float(total_income),
        },
        'expenses': {
            'items': [
                {'name': 'Staff Salaries & Benefits', 'amount': float(staff_costs)},
                {'name': 'Rent & Utilities',          'amount': float(rent_util)},
                {'name': 'M-Pesa Transaction Costs',  'amount': float(mpesa_costs)},
                {'name': 'Loan Loss Provision',       'amount': float(loan_loss)},
                {'name': 'Admin & Other',             'amount': float(admin_exp)},
            ],
            'total': float(total_expenses),
        },
        'net_profit':    float(net_profit),
        'profit_margin': round(float(net_profit / total_income * 100), 2) if total_income else 0,
    }


def balance_sheet(as_at_date=None):
    """Balance Sheet as at a given date."""
    as_at = as_at_date or timezone.now().date()

    def bs_balance(prefix, normal='debit'):
        qs = JournalLine.objects.filter(
            account__code__startswith=prefix,
            entry__status='POSTED',
            entry__date__lte=as_at,
        )
        agg = qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
        d = agg['d'] or Decimal('0')
        c = agg['c'] or Decimal('0')
        return float(d - c if normal == 'debit' else c - d)

    # Assets
    cash_mpesa       = bs_balance('1010')
    cash_bank        = bs_balance('1011')
    loans_recv       = bs_balance('1100')
    interest_recv    = bs_balance('1110')
    penalty_recv     = bs_balance('1115')
    prepaid          = bs_balance('1200')
    fixed_assets     = bs_balance('1500')
    loan_loss_res    = bs_balance('6010', 'credit')   # contra asset
    net_loans        = loans_recv - loan_loss_res

    total_current    = cash_mpesa + cash_bank + interest_recv + penalty_recv + prepaid
    total_non_curr   = fixed_assets
    total_assets     = total_current + net_loans + total_non_curr

    # Liabilities
    accounts_pay     = bs_balance('2010', 'credit')
    accrued_int      = bs_balance('2020', 'credit')
    cust_deposits    = bs_balance('2030', 'credit')
    total_liab       = accounts_pay + accrued_int + cust_deposits

    # Equity
    share_capital    = bs_balance('3010', 'credit')
    retained         = bs_balance('3020', 'credit')
    # Add current period profit (income - expenses)
    today            = timezone.now().date()
    year_start       = today.replace(month=1, day=1)
    pl_result        = income_statement(year_start, today)
    current_profit   = pl_result['net_profit']
    total_equity     = share_capital + retained + current_profit
    total_liab_equity= total_liab + total_equity

    return {
        'as_at': str(as_at),
        'assets': {
            'current': [
                {'name': 'Cash & M-Pesa Float', 'amount': cash_mpesa},
                {'name': 'Cash at Bank',         'amount': cash_bank},
                {'name': 'Interest Receivable',  'amount': interest_recv},
                {'name': 'Penalty Receivable',   'amount': penalty_recv},
                {'name': 'Prepaid Expenses',     'amount': prepaid},
            ],
            'current_total': total_current,
            'loans': [
                {'name': 'Loans Receivable (Gross)', 'amount': loans_recv},
                {'name': 'Less: Loan Loss Reserve',  'amount': -loan_loss_res},
                {'name': 'Loans Receivable (Net)',   'amount': net_loans},
            ],
            'non_current': [
                {'name': 'Fixed Assets (Net)', 'amount': fixed_assets},
            ],
            'non_current_total': total_non_curr,
            'total': total_assets,
        },
        'liabilities': {
            'items': [
                {'name': 'Accounts Payable',   'amount': accounts_pay},
                {'name': 'Accrued Interest',   'amount': accrued_int},
                {'name': 'Customer Deposits',  'amount': cust_deposits},
            ],
            'total': total_liab,
        },
        'equity': {
            'items': [
                {'name': 'Share Capital',        'amount': share_capital},
                {'name': 'Retained Earnings',    'amount': retained},
                {'name': 'Net Profit (Current)', 'amount': current_profit},
            ],
            'total': total_equity,
        },
        'total_liabilities_equity': total_liab_equity,
        'balanced': abs(total_assets - total_liab_equity) < 0.01,
    }


def trial_balance(as_at_date=None):
    """Trial Balance — all accounts with non-zero balances."""
    as_at = as_at_date or timezone.now().date()
    accounts = Account.objects.filter(is_active=True).order_by('code')
    rows = []
    total_dr = Decimal('0')
    total_cr = Decimal('0')

    for acc in accounts:
        qs = JournalLine.objects.filter(
            account=acc,
            entry__status='POSTED',
            entry__date__lte=as_at,
        )
        agg = qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
        d = agg['d'] or Decimal('0')
        c = agg['c'] or Decimal('0')
        if d == 0 and c == 0:
            continue
        # Normal balance side
        if acc.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            balance = d - c
            row = {'code': acc.code, 'name': acc.name, 'type': acc.account_type,
                   'debit': float(balance) if balance >= 0 else 0,
                   'credit': float(-balance) if balance < 0 else 0}
        else:
            balance = c - d
            row = {'code': acc.code, 'name': acc.name, 'type': acc.account_type,
                   'debit': float(-balance) if balance < 0 else 0,
                   'credit': float(balance) if balance >= 0 else 0}
        total_dr += Decimal(str(row['debit']))
        total_cr += Decimal(str(row['credit']))
        rows.append(row)

    return {
        'as_at':     str(as_at),
        'accounts':  rows,
        'total_dr':  float(total_dr),
        'total_cr':  float(total_cr),
        'balanced':  abs(float(total_dr) - float(total_cr)) < 0.01,
    }


def general_ledger(account_code, date_from=None, date_to=None):
    """All transactions for a single GL account."""
    acc = Account.objects.get(code=account_code)
    qs  = JournalLine.objects.filter(account=acc, entry__status='POSTED')
    if date_from:
        qs = qs.filter(entry__date__gte=date_from)
    if date_to:
        qs = qs.filter(entry__date__lte=date_to)
    qs  = qs.select_related('entry', 'branch').order_by('entry__date', 'entry__id')

    running_balance = Decimal('0')
    lines = []
    for line in qs:
        if acc.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            running_balance += line.debit_amount - line.credit_amount
        else:
            running_balance += line.credit_amount - line.debit_amount
        lines.append({
            'date':        str(line.entry.date),
            'reference':   line.entry.reference,
            'narration':   line.entry.narration,
            'debit':       float(line.debit_amount),
            'credit':      float(line.credit_amount),
            'balance':     float(running_balance),
            'branch':      line.branch.name if line.branch else None,
        })

    return {
        'account': {'code': acc.code, 'name': acc.name, 'type': acc.account_type},
        'lines':   lines,
        'closing_balance': float(running_balance),
    }
