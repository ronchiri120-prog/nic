"""
loans/pricing.py
Business rules for loan pricing at QuickLender.

RATE SCHEDULE:
  Platinum client  → 16%   (≥5 fully repaid loans, zero arrears history)
  Gold client      → 18%   (≥3 fully repaid loans, ≤1 arrears incident)
  Silver client    → 20%   (standard / new customer)
  Arrears penalty  → 21%   (3+ consecutive missed repayments on current loan)

PROCESSING FEES:
  First loan       → KES 500
  Repeat loan      → KES 300

TIER PROMOTION RULES:
  Silver  → Gold:      3 fully repaid loans with no missed payments
  Gold    → Platinum:  5 fully repaid loans with no arrears in last 12 months
  Demotion (Platinum/Gold → Silver): any write-off OR 3+ arrears incidents in 12 months

ARREARS RULE:
  If arrears_count >= 3 on current active loan → rate jumps to 21% for that loan
  (does NOT affect tier — tier recalculated on next application)
"""
from decimal import Decimal
from django.utils import timezone
import datetime


# ─── Rate constants ────────────────────────────────────────────────────────────
RATE_PLATINUM = Decimal('16')
RATE_GOLD     = Decimal('18')
RATE_SILVER   = Decimal('20')
RATE_ARREARS  = Decimal('21')

FEE_FIRST_LOAN  = Decimal('500')
FEE_REPEAT_LOAN = Decimal('300')


def get_customer_tier(customer) -> str:
    """
    Compute the current tier for a customer based on their repayment history.
    Returns: 'PLATINUM' | 'GOLD' | 'SILVER'
    """
    from apps.loans.models import Loan

    # All closed (fully repaid) loans — not written off, not in default
    clean_loans = Loan.objects.filter(
        customer=customer,
        status='CLOSED',
    ).exclude(notes__icontains='write-off').count()

    # Any loans written off = immediate Silver
    written_off = Loan.objects.filter(
        customer=customer,
        status='WRITTEN_OFF',
    ).count()

    if written_off > 0:
        return 'SILVER'

    # Arrears incidents in last 12 months (loans that ever hit arrears_count >= 3)
    one_year_ago = timezone.now() - datetime.timedelta(days=365)
    arrears_incidents = Loan.objects.filter(
        customer=customer,
        arrears_count__gte=3,
        created_at__gte=one_year_ago,
    ).count()

    if arrears_incidents >= 3:
        return 'SILVER'

    # Platinum: 5+ clean loans, zero arrears incidents in 12 months
    if clean_loans >= 5 and arrears_incidents == 0:
        return 'PLATINUM'

    # Gold: 3+ clean loans, at most 1 arrears incident
    if clean_loans >= 3 and arrears_incidents <= 1:
        return 'GOLD'

    return 'SILVER'


def recalculate_and_save_tier(customer, user=None) -> dict:
    """
    Recalculate tier and update customer record.
    Called after each loan closes or arrears threshold is reached.
    Returns info about the change.
    """
    old_tier = customer.tier
    new_tier = get_customer_tier(customer)

    if old_tier != new_tier:
        customer.tier           = new_tier
        customer.tier_updated_at = timezone.now()
        customer.tier_notes     = (
            f'Auto-recalculated on {timezone.now().strftime("%d %b %Y")}. '
            f'{old_tier} → {new_tier}.'
        )
        customer.save(update_fields=['tier', 'tier_updated_at', 'tier_notes'])

        # Log to audit
        try:
            from apps.accounts.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action=f'Tier change: {old_tier} → {new_tier}',
                model_name='Customer',
                object_id=str(customer.id),
                details={
                    'uid': customer.uid,
                    'name': customer.full_name,
                    'old_tier': old_tier,
                    'new_tier': new_tier,
                },
            )
        except Exception:
            pass

    return {'changed': old_tier != new_tier, 'old': old_tier, 'new': new_tier}


def get_effective_rate(customer, product, current_loan=None) -> Decimal:
    """
    Return the actual interest rate to apply for a loan.

    Priority:
      1. If current loan has arrears_count >= 3 → 21%
      2. Customer tier rate (Platinum=16%, Gold=18%, Silver=20%)
      3. Falls back to product.interest_rate if no tier rates configured
    """
    # Arrears override (active loan that has missed 3+ repayments)
    if current_loan and getattr(current_loan, 'arrears_count', 0) >= 3:
        return RATE_ARREARS

    # Tier-based rate
    tier = getattr(customer, 'tier', 'SILVER') or 'SILVER'

    if product:
        if tier == 'PLATINUM':
            return Decimal(str(product.rate_platinum or RATE_PLATINUM))
        elif tier == 'GOLD':
            return Decimal(str(product.rate_gold or RATE_GOLD))
        else:
            return Decimal(str(product.rate_silver or RATE_SILVER))
    else:
        # No product — use hardcoded defaults
        return {'PLATINUM': RATE_PLATINUM, 'GOLD': RATE_GOLD}.get(tier, RATE_SILVER)


def get_processing_fee(customer, product=None) -> tuple[Decimal, bool]:
    """
    Return (processing_fee, is_first_loan).
    First loan = no previously CLOSED or ACTIVE loans.
    """
    from apps.loans.models import Loan
    prior_loans = Loan.objects.filter(
        customer=customer,
        status__in=['CLOSED', 'ACTIVE', 'DEFAULT'],
    ).count()

    is_first = prior_loans == 0
    if product:
        fee = Decimal(str(product.first_loan_fee if is_first else product.repeat_loan_fee))
    else:
        fee = FEE_FIRST_LOAN if is_first else FEE_REPEAT_LOAN

    return fee, is_first


def apply_arrears_rate(loan) -> bool:
    """
    Check if loan has hit the arrears threshold (3+ consecutive missed payments).
    If yes, update effective_rate to 21% and save.
    Returns True if rate was changed.
    """
    if loan.arrears_count >= 3 and loan.effective_rate != RATE_ARREARS:
        old_rate           = loan.effective_rate or loan.interest_rate
        loan.effective_rate = RATE_ARREARS
        loan.notes = (loan.notes or '') + (
            f'\n[ARREARS RATE {timezone.now().date()}] '
            f'Rate raised from {old_rate}% to {RATE_ARREARS}% '
            f'after {loan.arrears_count} missed repayments.'
        )
        loan.save(update_fields=['effective_rate', 'notes'])
        return True
    return False


def price_new_loan(customer, principal: Decimal, product) -> dict:
    """
    Calculate all pricing components for a new loan application.
    Returns dict consumed by the loan creation serializer.
    """
    # Recalculate tier before pricing
    recalculate_and_save_tier(customer)

    rate          = get_effective_rate(customer, product)
    fee, is_first = get_processing_fee(customer, product)
    interest      = (principal * rate / 100).quantize(Decimal('0.01'))
    total         = principal + interest + fee

    tenure        = product.tenure_days if product else 30

    return {
        'interest_rate':   float(rate),
        'effective_rate':  float(rate),
        'interest_amount': float(interest),
        'processing_fee':  float(fee),
        'is_first_loan':   is_first,
        'initiation_fee':  float(fee),   # keep legacy field in sync
        'total_amount':    float(total),
        'balance':         float(total),
        'tier_applied':    customer.tier,
        'tier_note': (
            f"{'First loan — KES 500 processing fee' if is_first else 'Repeat loan — KES 300 processing fee'}. "
            f"{customer.tier} tier — {rate}% rate."
        ),
    }
