"""
loans/schedule.py
Generates and manages loan repayment schedules.
Supports: flat (single bullet), reducing balance, equal instalments.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone


SCHEDULE_TYPES = {
    'BULLET':    'Single repayment at maturity',
    'EQUAL':     'Equal instalments (principal + interest split evenly)',
    'REDUCING':  'Reducing balance (equal principal, reducing interest)',
}


def _round(v):
    return Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def generate_schedule(loan, schedule_type: str = 'BULLET', num_instalments: int = 1) -> list[dict]:
    """
    Generate a repayment schedule for a loan.

    Args:
        loan:             Loan instance (must have principal, interest_amount,
                          total_amount, disbursed_at or created_at, tenure_days)
        schedule_type:    BULLET | EQUAL | REDUCING
        num_instalments:  Number of instalments (ignored for BULLET)

    Returns:
        List of dicts: [{installment, due_date, principal_due,
                         interest_due, total_due, balance_after}]
    """
    start_date   = (loan.disbursed_at.date() if loan.disbursed_at
                    else timezone.now().date())
    total_days   = loan.tenure_days or 30
    principal    = Decimal(str(loan.principal))
    interest     = Decimal(str(loan.interest_amount))
    total        = principal + interest

    if schedule_type == 'BULLET' or num_instalments <= 1:
        return [{
            'installment':    1,
            'due_date':       start_date + timedelta(days=total_days),
            'principal_due':  _round(principal),
            'interest_due':   _round(interest),
            'total_due':      _round(total),
            'balance_after':  Decimal('0.00'),
        }]

    # Instalment interval
    interval_days = total_days // num_instalments
    rows          = []
    balance       = principal

    if schedule_type == 'EQUAL':
        # Split principal + interest evenly
        inst_principal = _round(principal / num_instalments)
        inst_interest  = _round(interest  / num_instalments)
        inst_total     = inst_principal + inst_interest

        for i in range(1, num_instalments + 1):
            due = start_date + timedelta(days=interval_days * i)
            # Absorb rounding on last instalment
            if i == num_instalments:
                inst_principal = _round(balance)
            balance = _round(max(balance - inst_principal, Decimal('0')))
            rows.append({
                'installment':    i,
                'due_date':       due,
                'principal_due':  inst_principal,
                'interest_due':   inst_interest,
                'total_due':      inst_principal + inst_interest,
                'balance_after':  balance,
            })

    elif schedule_type == 'REDUCING':
        # Equal principal, reducing interest
        monthly_rate      = Decimal(str(loan.interest_rate)) / 100 / (30 / interval_days)
        inst_principal    = _round(principal / num_instalments)

        for i in range(1, num_instalments + 1):
            due             = start_date + timedelta(days=interval_days * i)
            inst_interest   = _round(balance * monthly_rate)
            if i == num_instalments:
                inst_principal = _round(balance)
            balance         = _round(max(balance - inst_principal, Decimal('0')))
            rows.append({
                'installment':    i,
                'due_date':       due,
                'principal_due':  inst_principal,
                'interest_due':   inst_interest,
                'total_due':      inst_principal + inst_interest,
                'balance_after':  balance,
            })

    return rows


def save_schedule(loan, rows: list[dict]):
    """Persist schedule rows to DB (replaces any existing schedule)."""
    from apps.loans.models import RepaymentSchedule
    RepaymentSchedule.objects.filter(loan=loan).delete()
    objs = [
        RepaymentSchedule(
            loan         = loan,
            installment  = r['installment'],
            due_date     = r['due_date'],
            amount_due   = r['total_due'],
            amount_paid  = Decimal('0'),
        )
        for r in rows
    ]
    RepaymentSchedule.objects.bulk_create(objs)
    return len(objs)


def get_next_due(loan):
    """Return the next unpaid instalment row, or None if all paid."""
    from apps.loans.models import RepaymentSchedule
    return (RepaymentSchedule.objects
            .filter(loan=loan, status='PENDING')
            .order_by('due_date')
            .first())
