"""
loans/restructuring.py
Loan restructuring workflows:
  - Extend tenure (reduce monthly burden)
  - Rate reduction (goodwill / hardship)
  - Top-up (additional funds on active loan)
  - Rollover (new loan replaces old)
  - Write-off (partial or full)
"""
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
import datetime


def extend_tenure(loan, new_tenure_days: int, user=None, reason: str = '') -> dict:
    """
    Extend the loan repayment period.
    Recalculates due date without changing the outstanding balance.
    Creates an audit trail entry.
    """
    if loan.status != 'ACTIVE':
        raise ValueError(f'Only ACTIVE loans can be restructured (current: {loan.status})')
    if new_tenure_days <= loan.tenure_days:
        raise ValueError(f'New tenure ({new_tenure_days}d) must be longer than current ({loan.tenure_days}d)')

    with transaction.atomic():
        old_due    = loan.due_date
        old_tenure = loan.tenure_days

        loan.tenure_days = new_tenure_days
        loan.due_date    = (timezone.now() + datetime.timedelta(days=new_tenure_days)).date()
        loan.notes = (loan.notes or '') + (
            f'\n[RESTRUCTURE {timezone.now().date()}] Tenure extended: '
            f'{old_tenure}d → {new_tenure_days}d. '
            f'Due date: {old_due} → {loan.due_date}. '
            f'By: {user.full_name if user else "system"}. '
            f'Reason: {reason}'
        )
        loan.save(update_fields=['tenure_days', 'due_date', 'notes'])

        _log_restructure(loan, 'TENURE_EXTENSION', user, reason, {
            'old_tenure': old_tenure,
            'new_tenure': new_tenure_days,
            'old_due_date': str(old_due),
            'new_due_date': str(loan.due_date),
        })

    return {
        'loan_id':      loan.loan_id,
        'action':       'TENURE_EXTENSION',
        'old_due_date': str(old_due),
        'new_due_date': str(loan.due_date),
        'new_tenure':   new_tenure_days,
    }


def reduce_interest_rate(loan, new_rate: Decimal, user=None, reason: str = '') -> dict:
    """
    Reduce the interest rate on an active loan (goodwill / CBK hardship directive).
    Recalculates the outstanding balance.
    """
    if loan.status != 'ACTIVE':
        raise ValueError(f'Only ACTIVE loans can be restructured')
    if new_rate >= loan.interest_rate:
        raise ValueError(f'New rate ({new_rate}%) must be lower than current ({loan.interest_rate}%)')

    with transaction.atomic():
        old_rate    = loan.interest_rate
        old_total   = loan.total_amount
        old_balance = loan.balance

        # Recalculate on remaining principal
        paid_principal = loan.total_paid * (loan.principal / loan.total_amount) if loan.total_amount else Decimal('0')
        remaining_principal = loan.principal - paid_principal
        new_interest  = remaining_principal * (new_rate / 100)

        loan.interest_rate   = new_rate
        loan.interest_amount = new_interest
        loan.total_amount    = loan.principal + new_interest + loan.initiation_fee
        loan.balance         = loan.total_amount + loan.penalty_amount - loan.total_paid
        loan.notes = (loan.notes or '') + (
            f'\n[RESTRUCTURE {timezone.now().date()}] Rate reduced: '
            f'{old_rate}% → {new_rate}%. '
            f'Balance adjusted from KES {old_balance:,.0f} to KES {loan.balance:,.0f}. '
            f'By: {user.full_name if user else "system"}. Reason: {reason}'
        )
        loan.save(update_fields=['interest_rate','interest_amount','total_amount','balance','notes'])

        _log_restructure(loan, 'RATE_REDUCTION', user, reason, {
            'old_rate': float(old_rate),
            'new_rate': float(new_rate),
            'old_balance': float(old_balance),
            'new_balance': float(loan.balance),
        })

    return {
        'loan_id':     loan.loan_id,
        'action':      'RATE_REDUCTION',
        'old_rate':    float(old_rate),
        'new_rate':    float(new_rate),
        'new_balance': float(loan.balance),
    }


def topup_loan(loan, topup_amount: Decimal, user=None, reason: str = '') -> dict:
    """
    Add additional funds to an active loan.
    Increases principal, recalculates balance.
    """
    if loan.status != 'ACTIVE':
        raise ValueError('Only ACTIVE loans can be topped up')
    if topup_amount <= 0:
        raise ValueError('Top-up amount must be positive')

    with transaction.atomic():
        old_principal = loan.principal
        old_balance   = loan.balance

        extra_interest = topup_amount * (loan.interest_rate / 100)
        loan.principal       += topup_amount
        loan.interest_amount += extra_interest
        loan.total_amount    += topup_amount + extra_interest
        loan.balance         += topup_amount + extra_interest
        loan.notes = (loan.notes or '') + (
            f'\n[TOP-UP {timezone.now().date()}] '
            f'KES {topup_amount:,.0f} added. '
            f'Principal: KES {old_principal:,.0f} → KES {loan.principal:,.0f}. '
            f'By: {user.full_name if user else "system"}.'
        )
        loan.save(update_fields=['principal','interest_amount','total_amount','balance','notes'])

        _log_restructure(loan, 'TOP_UP', user, reason, {
            'topup_amount':  float(topup_amount),
            'old_principal': float(old_principal),
            'new_principal': float(loan.principal),
            'new_balance':   float(loan.balance),
        })

        # Post to GL
        try:
            from apps.accounting.gl_service import _post, GL
            _post(
                narration   = f'Loan top-up — {loan.loan_id}',
                source_type = 'topup',
                source_id   = loan.id,
                lines=[
                    (GL.LOANS_RECEIVABLE, float(topup_amount), 0,                    f'Top-up — {loan.loan_id}', loan.branch),
                    (GL.CASH_MPESA,       0,                   float(topup_amount),  f'Funds out — top-up',       loan.branch),
                ],
                user=user,
            )
        except Exception:
            pass

    return {
        'loan_id':     loan.loan_id,
        'action':      'TOP_UP',
        'topup_amount': float(topup_amount),
        'new_principal': float(loan.principal),
        'new_balance':   float(loan.balance),
    }


def partial_write_off(loan, writeoff_amount: Decimal, user=None, reason: str = '') -> dict:
    """
    Write off part of the balance (penalty / interest waiver).
    Posts to GL and updates loan balance.
    """
    if loan.status not in ('ACTIVE', 'DEFAULT'):
        raise ValueError('Only ACTIVE or DEFAULT loans can be written off')
    if writeoff_amount > loan.balance:
        raise ValueError(f'Write-off KES {writeoff_amount:,.0f} exceeds balance KES {loan.balance:,.0f}')

    with transaction.atomic():
        old_balance = loan.balance
        loan.balance -= writeoff_amount
        if loan.balance <= 0:
            loan.balance   = Decimal('0')
            loan.status    = 'CLOSED'
            loan.closed_at = timezone.now()
        loan.notes = (loan.notes or '') + (
            f'\n[WRITE-OFF {timezone.now().date()}] '
            f'KES {writeoff_amount:,.0f} written off. '
            f'Balance: KES {old_balance:,.0f} → KES {loan.balance:,.0f}. '
            f'By: {user.full_name if user else "system"}. Reason: {reason}'
        )
        loan.save(update_fields=['balance','status','closed_at','notes'])

        _log_restructure(loan, 'WRITE_OFF', user, reason, {
            'writeoff_amount': float(writeoff_amount),
            'old_balance':     float(old_balance),
            'new_balance':     float(loan.balance),
        })

        try:
            from apps.accounting.gl_service import post_loan_write_off
            post_loan_write_off(loan, amount=writeoff_amount, user=user)
        except Exception:
            pass

    return {
        'loan_id':        loan.loan_id,
        'action':         'WRITE_OFF',
        'writeoff_amount': float(writeoff_amount),
        'new_balance':     float(loan.balance),
        'loan_status':     loan.status,
    }


def _log_restructure(loan, action_type, user, reason, metadata):
    """Log restructure action to audit trail."""
    try:
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user       = user,
            action     = f'Loan Restructure: {action_type}',
            model_name = 'Loan',
            object_id  = str(loan.id),
            details    = {'loan_id': loan.loan_id, 'reason': reason, **metadata},
        )
    except Exception:
        pass
