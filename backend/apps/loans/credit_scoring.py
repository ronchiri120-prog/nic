"""
loans/credit_scoring.py
Automated credit scoring engine for QuickLender loan applications.

Score range: 0–100
  80–100  Low risk    → auto-approve eligible
  60–79   Medium risk → recommend review
  40–59   High risk   → manual review required
  0–39    Very high   → recommend reject

Factors (weighted):
  1. Repayment history    25 pts  — past loans paid on time
  2. Income adequacy      20 pts  — monthly income vs loan amount
  3. Customer tenure      15 pts  — how long they've been a customer
  4. Active loan burden   15 pts  — existing outstanding balance ratio
  5. Employment stability 10 pts  — employment type and duration
  6. Guarantor quality    10 pts  — guarantor present and verified
  7. KYC completeness      5 pts  — docs, photo, contact info complete
"""
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List


@dataclass
class ScoreBreakdown:
    factor:    str
    max_score: int
    score:     int
    reason:    str


@dataclass
class CreditScoreResult:
    customer_id:   int
    loan_amount:   Decimal
    score:         int
    risk_grade:    str
    recommendation:str
    breakdown:     List[ScoreBreakdown]
    flags:         List[str]
    approved:      bool

    @property
    def risk_color(self):
        if   self.score >= 80: return 'green'
        elif self.score >= 60: return 'amber'
        elif self.score >= 40: return 'orange'
        return 'red'


def score_loan_application(customer, loan_amount: Decimal, product=None) -> CreditScoreResult:
    """
    Run the full credit scoring model for a customer + loan amount.

    Args:
        customer:    Customer model instance
        loan_amount: Requested loan amount (Decimal)
        product:     LoanProduct instance (optional)

    Returns:
        CreditScoreResult with score, grade, recommendation, and breakdown
    """
    breakdown = []
    flags     = []
    total     = 0

    # ── 1. REPAYMENT HISTORY (25 pts) ────────────────────────────────────────
    past_loans = customer.loans.filter(status__in=['CLOSED','DEFAULT','WRITTEN_OFF','ACTIVE'])
    closed     = past_loans.filter(status='CLOSED').count()
    defaults   = past_loans.filter(status__in=['DEFAULT','WRITTEN_OFF']).count()
    total_past = past_loans.count()

    if total_past == 0:
        pts    = 15   # New customer — moderate score
        reason = 'New customer — no credit history'
    elif defaults == 0:
        rate   = closed / total_past
        pts    = int(25 * rate) if rate >= 0.9 else int(20 * rate)
        reason = f'{closed}/{total_past} loans fully repaid'
    else:
        def_rate = defaults / total_past
        pts      = max(0, int(25 * (1 - def_rate * 2)))
        reason   = f'{defaults} default(s) on record'
        if defaults >= 2:
            flags.append(f'Multiple defaults ({defaults}) — high risk')

    pts = min(25, pts)
    total += pts
    breakdown.append(ScoreBreakdown('Repayment history', 25, pts, reason))

    # ── 2. INCOME ADEQUACY (20 pts) ──────────────────────────────────────────
    income = float(customer.monthly_income or 0)
    amount = float(loan_amount)

    if income == 0:
        pts    = 0
        reason = 'No income recorded'
        flags.append('No income data — cannot assess debt service capacity')
    else:
        dti = amount / (income * 3)   # Loan as % of 3 months income
        if   dti <= 0.3:  pts, reason = 20, f'Loan is {dti*100:.0f}% of 3-month income — excellent'
        elif dti <= 0.5:  pts, reason = 16, f'Loan is {dti*100:.0f}% of 3-month income — good'
        elif dti <= 0.8:  pts, reason = 10, f'Loan is {dti*100:.0f}% of 3-month income — stretched'
        elif dti <= 1.2:  pts, reason = 5,  f'Loan is {dti*100:.0f}% of 3-month income — high'
        else:
            pts, reason = 0, f'Loan is {dti*100:.0f}% of 3-month income — unaffordable'
            flags.append('Loan amount exceeds 1.2x three-month income — likely unaffordable')

    total += pts
    breakdown.append(ScoreBreakdown('Income adequacy', 20, pts, reason))

    # ── 3. CUSTOMER TENURE (15 pts) ──────────────────────────────────────────
    from django.utils import timezone
    days = (timezone.now().date() - customer.created_at.date()).days
    if   days >= 730:  pts, reason = 15, f'{days//365} years as customer'
    elif days >= 365:  pts, reason = 12, f'{days//30} months as customer'
    elif days >= 180:  pts, reason = 8,  f'{days//30} months as customer'
    elif days >= 90:   pts, reason = 5,  f'{days} days — recent customer'
    else:
        pts, reason = 2,  f'{days} days — very new customer'
        flags.append('Customer registered within 90 days')

    total += pts
    breakdown.append(ScoreBreakdown('Customer tenure', 15, pts, reason))

    # ── 4. ACTIVE LOAN BURDEN (15 pts) ───────────────────────────────────────
    from django.db.models import Sum
    active_balance = customer.loans.filter(
        status='ACTIVE'
    ).aggregate(s=Sum('balance'))['s'] or Decimal('0')

    if active_balance == 0:
        pts, reason = 15, 'No existing active loans'
    else:
        burden_ratio = float(active_balance) / max(income * 3, 1)
        if   burden_ratio <= 0.3: pts, reason = 12, f'Active balance KES {active_balance:,.0f} — manageable'
        elif burden_ratio <= 0.6: pts, reason = 8,  f'Active balance KES {active_balance:,.0f} — moderate'
        elif burden_ratio <= 1.0: pts, reason = 4,  f'Active balance KES {active_balance:,.0f} — high'
        else:
            pts, reason = 0, f'Active balance KES {active_balance:,.0f} — over-leveraged'
            flags.append(f'Customer already has KES {active_balance:,.0f} outstanding — over-leveraged')

    total += pts
    breakdown.append(ScoreBreakdown('Active loan burden', 15, pts, reason))

    # ── 5. EMPLOYMENT STABILITY (10 pts) ─────────────────────────────────────
    emp_type = (customer.employment_type or '').lower()
    employer = (customer.employer or '').strip()
    if   'permanent' in emp_type or 'civil' in emp_type or 'government' in emp_type:
        pts, reason = 10, f'Permanent/government employment at {employer or "employer"}'
    elif 'contract' in emp_type:
        pts, reason = 7,  f'Contract employment at {employer or "employer"}'
    elif 'self' in emp_type or 'business' in emp_type:
        pts, reason = 6,  f'Self-employed / business owner'
    elif employer:
        pts, reason = 5,  f'Employed at {employer}'
    else:
        pts, reason = 2,  'No employment information provided'
        flags.append('Employment details missing')

    total += pts
    breakdown.append(ScoreBreakdown('Employment stability', 10, pts, reason))

    # ── 6. GUARANTOR (10 pts) ────────────────────────────────────────────────
    has_guarantor  = bool(customer.guarantor_name and customer.guarantor_phone)
    has_guarantor_id = bool(customer.guarantor_id)
    if has_guarantor and has_guarantor_id:
        pts, reason = 10, f'Verified guarantor: {customer.guarantor_name}'
    elif has_guarantor:
        pts, reason = 6,  f'Guarantor present (ID not verified): {customer.guarantor_name}'
    else:
        pts, reason = 0,  'No guarantor on file'
        flags.append('No guarantor — higher credit risk')

    total += pts
    breakdown.append(ScoreBreakdown('Guarantor quality', 10, pts, reason))

    # ── 7. KYC COMPLETENESS (5 pts) ──────────────────────────────────────────
    kyc_checks = [
        bool(customer.national_id),
        bool(customer.phone),
        bool(customer.dob),
        bool(customer.address),
        bool(customer.id_front or customer.id_back),
    ]
    complete = sum(kyc_checks)
    pts      = complete  # 0–5
    reason   = f'{complete}/5 KYC fields complete'
    if complete < 3:
        flags.append(f'Incomplete KYC ({complete}/5) — verification required')

    total += pts
    breakdown.append(ScoreBreakdown('KYC completeness', 5, pts, reason))

    # ── HARD STOPS ────────────────────────────────────────────────────────────
    if customer.status == 'BLACKLISTED':
        total = 0
        flags.insert(0, 'BLACKLISTED customer — automatic rejection')

    if defaults >= 3:
        total = min(total, 30)
        flags.insert(0, 'Three or more defaults — capped at 30')

    # ── GRADE & RECOMMENDATION ───────────────────────────────────────────────
    score = min(100, max(0, total))

    if   score >= 80: grade, rec, approved = 'A — Low risk',       'Auto-approve',        True
    elif score >= 65: grade, rec, approved = 'B — Medium risk',    'Recommend approval',   True
    elif score >= 50: grade, rec, approved = 'C — Elevated risk',  'Manual review',        False
    elif score >= 35: grade, rec, approved = 'D — High risk',      'Recommend rejection',  False
    else:             grade, rec, approved = 'E — Very high risk', 'Reject',               False

    # Loan limit check
    if customer.loan_limit and loan_amount > customer.loan_limit:
        flags.append(f'Requested KES {loan_amount:,.0f} exceeds customer limit KES {customer.loan_limit:,.0f}')
        approved = False

    return CreditScoreResult(
        customer_id    = customer.id,
        loan_amount    = loan_amount,
        score          = score,
        risk_grade     = grade,
        recommendation = rec,
        breakdown      = breakdown,
        flags          = flags,
        approved       = approved,
    )
