"""
accounting/gl_service.py
Business logic for auto-posting journal entries on loan events.
Maintains the double-entry ledger automatically.
"""
from decimal import Decimal
from django.utils import timezone
from .models import Account, JournalEntry, JournalLine


# ─── ACCOUNT CODE CONSTANTS ─────────────────────────────────────────────────
class GL:
    # Assets
    CASH_MPESA        = '1010'
    CASH_BANK         = '1011'
    LOANS_RECEIVABLE  = '1100'
    INTEREST_RECV     = '1110'
    PENALTY_RECV      = '1115'
    PREPAID_EXPENSES  = '1200'
    FIXED_ASSETS      = '1500'

    # Liabilities
    ACCOUNTS_PAYABLE  = '2010'
    ACCRUED_INTEREST  = '2020'
    CUSTOMER_DEPOSITS = '2030'

    # Equity
    SHARE_CAPITAL     = '3010'
    RETAINED_EARNINGS = '3020'

    # Income
    INTEREST_INCOME   = '4010'
    FEE_INCOME        = '4020'
    PENALTY_INCOME    = '4030'

    # Expenses
    STAFF_COSTS       = '5010'
    RENT_UTILITIES    = '5020'
    MPESA_COSTS       = '5030'
    LOAN_LOSS_PROV    = '5040'
    ADMIN_EXPENSES    = '5050'

    # Contra / Provisions
    LOAN_LOSS_RESERVE = '6010'


def _get(code):
    try:
        return Account.objects.get(code=code)
    except Account.DoesNotExist:
        raise ValueError(f'GL account {code} not found — run seed_chart_of_accounts first')


def _post(narration, source_type, source_id, lines, date=None, user=None):
    """Create and immediately post a balanced journal entry."""
    entry = JournalEntry.objects.create(
        narration   = narration,
        date        = date or timezone.now().date(),
        source_type = source_type,
        source_id   = source_id,
        created_by  = user,
    )
    for account_code, debit, credit, desc, branch in lines:
        JournalLine.objects.create(
            entry         = entry,
            account       = _get(account_code),
            debit_amount  = Decimal(str(debit)),
            credit_amount = Decimal(str(credit)),
            description   = desc,
            branch        = branch,
        )
    entry.post(user=user)
    return entry


# ─── AUTO-POST FUNCTIONS ─────────────────────────────────────────────────────

def post_loan_disbursement(loan, user=None):
    """
    DR  Loans Receivable         principal
    CR  Cash / M-Pesa Float      principal
    """
    p = loan.principal
    method_account = GL.CASH_MPESA if loan.disbursement_method == 'MPESA' else GL.CASH_BANK
    return _post(
        narration   = f'Loan disbursement — {loan.loan_id} ({loan.customer.full_name})',
        source_type = 'loan_disbursement',
        source_id   = loan.id,
        lines=[
            (GL.LOANS_RECEIVABLE, p,   0,  f'Principal — {loan.loan_id}', loan.branch),
            (method_account,      0,   p,  f'Funds out — {loan.disbursement_method}', loan.branch),
        ],
        user=user,
    )


def post_interest_accrual(loan, user=None):
    """
    DR  Interest Receivable      interest_amount
    CR  Interest Income          interest_amount
    """
    i = loan.interest_amount
    return _post(
        narration   = f'Interest accrual — {loan.loan_id}',
        source_type = 'interest_accrual',
        source_id   = loan.id,
        lines=[
            (GL.INTEREST_RECV,   i, 0, f'Interest — {loan.loan_id}', loan.branch),
            (GL.INTEREST_INCOME, 0, i, f'Income — {loan.loan_id}',   loan.branch),
        ],
        user=user,
    )


def post_initiation_fee(loan, user=None):
    """
    DR  Cash / M-Pesa            initiation_fee
    CR  Fee Income               initiation_fee
    """
    if not loan.initiation_fee or loan.initiation_fee == 0:
        return None
    f = loan.initiation_fee
    method_account = GL.CASH_MPESA if loan.disbursement_method == 'MPESA' else GL.CASH_BANK
    return _post(
        narration   = f'Initiation fee — {loan.loan_id}',
        source_type = 'fee',
        source_id   = loan.id,
        lines=[
            (method_account, f, 0, f'Fee received — {loan.loan_id}', loan.branch),
            (GL.FEE_INCOME,  0, f, f'Fee income — {loan.loan_id}',   loan.branch),
        ],
        user=user,
    )


def post_payment_received(payment, user=None):
    """
    When a payment comes in we split it: principal repayment + interest collection.

    DR  Cash / M-Pesa            payment.amount
    CR  Loans Receivable         principal portion
    CR  Interest Receivable      interest portion
    """
    loan = payment.loan
    if float(loan.total_amount) == 0:
        return None

    # Proportion split: principal vs interest
    ratio     = float(loan.interest_amount) / float(loan.total_amount)
    amt       = payment.amount
    int_part  = (amt * Decimal(str(ratio))).quantize(Decimal('0.01'))
    prin_part = amt - int_part

    method_account = GL.CASH_MPESA if payment.method == 'MPESA' else (
        GL.CASH_BANK if payment.method == 'BANK' else GL.CASH_MPESA
    )

    lines = [
        (method_account,       amt,       0,         f'Payment — {payment.ref}',             loan.branch),
        (GL.LOANS_RECEIVABLE,  0,         prin_part, f'Principal repaid — {loan.loan_id}',    loan.branch),
    ]
    if int_part > 0:
        lines.append((GL.INTEREST_RECV, 0, int_part, f'Interest collected — {loan.loan_id}', loan.branch))

    return _post(
        narration   = f'Payment received — {payment.ref} ({loan.customer.full_name})',
        source_type = 'payment',
        source_id   = payment.id,
        lines       = lines,
        date        = payment.paid_at.date(),
        user        = user,
    )


def post_penalty_charge(loan, penalty_amount, user=None):
    """
    DR  Penalty Receivable       penalty_amount
    CR  Penalty Income           penalty_amount
    """
    p = Decimal(str(penalty_amount))
    return _post(
        narration   = f'Penalty charge — {loan.loan_id} ({(timezone.now().date())})',
        source_type = 'penalty',
        source_id   = loan.id,
        lines=[
            (GL.PENALTY_RECV,   p, 0, f'Penalty — {loan.loan_id}', loan.branch),
            (GL.PENALTY_INCOME, 0, p, f'Income  — {loan.loan_id}', loan.branch),
        ],
        user=user,
    )


def post_loan_write_off(loan, amount=None, user=None):
    """
    DR  Loan Loss Provision (expense)   amount
    CR  Loans Receivable                amount
    """
    amt = Decimal(str(amount or loan.balance))
    return _post(
        narration   = f'Write-off — {loan.loan_id} ({loan.customer.full_name})',
        source_type = 'write_off',
        source_id   = loan.id,
        lines=[
            (GL.LOAN_LOSS_PROV,   amt, 0,   f'Write-off expense — {loan.loan_id}', loan.branch),
            (GL.LOANS_RECEIVABLE, 0,   amt, f'Receivable cleared — {loan.loan_id}',loan.branch),
        ],
        user=user,
    )


def post_loan_loss_provision(amount, branch=None, user=None):
    """
    Monthly provision entry:
    DR  Loan Loss Provision Expense     amount
    CR  Loan Loss Reserve               amount
    """
    amt = Decimal(str(amount))
    return _post(
        narration   = f'Loan loss provision — {timezone.now().strftime("%b %Y")}',
        source_type = 'provision',
        source_id   = None,
        lines=[
            (GL.LOAN_LOSS_PROV,    amt, 0,   'Monthly provision expense', branch),
            (GL.LOAN_LOSS_RESERVE, 0,   amt, 'Reserve increase',          branch),
        ],
        user=user,
    )
