"""loans/models.py — Full Loan Lifecycle"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class LoanProduct(models.Model):
    class LoanType(models.TextChoices):
        # Daily Collections
        IDC = 'IDC', 'Individual Daily Collection (IDC)'
        EDC = 'EDC', 'Every Day Collection (EDC)'
        GDC = 'GDC', 'Group Daily Collection (GDC)'
        # Weekly Collections
        IWC = 'IWC', 'Individual Weekly Collection (IWC)'
        EWC = 'EWC', 'Every Week Collection (EWC)'
        GWC = 'GWC', 'Group Weekly Collection (GWC)'
        # Monthly & Other Frequencies
        IMC = 'IMC', 'Individual Monthly Collection (IMC)'
        IBC = 'IBC', 'Individual Bi-weekly Collection (IBC)'
        IQC = 'IQC', 'Individual Quarterly Collection (IQC)'
        # Legacy Types
        FA = 'FA', 'Salary Advance (FA)'
        CC = 'CC', 'Credit Check (CC)'
        LOGBOOK = 'LOGBOOK', 'Logbook Loan'
        CUSTOM = 'CUSTOM', 'Custom'

    name         = models.CharField(max_length=80)
    loan_type    = models.CharField(max_length=10, choices=LoanType.choices)
    min_amount   = models.DecimalField(max_digits=14, decimal_places=2)
    max_amount   = models.DecimalField(max_digits=14, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text='% per cycle')
    tenure_days  = models.IntegerField(help_text='Loan duration in days')
    penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.5'), help_text='% per day')
    initiation_fee = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                     help_text='Legacy — use first_loan_fee / repeat_loan_fee')

    # ── Processing fees (per business rules) ──────────────────────────────
    first_loan_fee  = models.DecimalField(max_digits=10, decimal_places=2, default=500,
                      help_text='Processing fee for first-time borrowers (KES 500)')
    repeat_loan_fee = models.DecimalField(max_digits=10, decimal_places=2, default=400,
                      help_text='Processing fee for repeat borrowers (KES 400)')

    # ── Tier interest rates ────────────────────────────────────────────────
    rate_silver   = models.DecimalField(max_digits=5, decimal_places=2, default=20,
                    help_text='Silver tier rate — standard (20%)')
    rate_gold     = models.DecimalField(max_digits=5, decimal_places=2, default=18,
                    help_text='Gold tier rate — good repayors (18%)')
    rate_platinum = models.DecimalField(max_digits=5, decimal_places=2, default=16,
                    help_text='Platinum tier rate — excellent clients (16%)')
    rate_arrears  = models.DecimalField(max_digits=5, decimal_places=2, default=21,
                    help_text='Arrears penalty rate — 3+ missed repayments (21%)')

    is_active    = models.BooleanField(default=True)
    
    # ── Verification Team Assignment ─────────────────────────────────────────────
    verification_team = models.ForeignKey('accounts.User', on_delete=models.SET_NULL,
                        null=True, blank=True, related_name='assigned_products',
                        limit_choices_to={'role': 'VERIFICATION_TEAM'},
                        help_text='Verification team member assigned to verify loans of this product')

    class Meta:
        db_table = 'ql_loan_products'

    def __str__(self):
        return f'{self.name} ({self.loan_type})'


class Loan(models.Model):
    class Status(models.TextChoices):
        PENDING    = 'PENDING',    'Pending Approval'
        VERIFIED   = 'VERIFIED',   'Verified by Team'
        APPROVED   = 'APPROVED',   'Approved'
        DISBURSED  = 'DISBURSED',  'Disbursed'
        ACTIVE     = 'ACTIVE',     'Active'
        CLOSED     = 'CLOSED',     'Closed'
        DEFAULT    = 'DEFAULT',    'Default'
        WRITTEN_OFF = 'WRITTEN_OFF', 'Written Off'
        REJECTED   = 'REJECTED',   'Rejected'

    class DefaultReason(models.TextChoices):
        SIMPLE_PAY_ERROR = 'SIMPLE_PAY_ERROR', 'Simple Pay system Error'
        ADVERSE_BUSINESS_CYCLE = 'ADVERSE_BUSINESS_CYCLE', 'Adverse Business Cycle'
        MPESA_NETWORK_DOWN = 'MPESA_NETWORK_DOWN', 'M-pesa Network Down'
        BFC_NOT_UNDERSTAND = 'BFC_NOT_UNDERSTAND', 'BFC-Did not Understand terms and Conditions'
        BFC_MARKET_INFLUENCE = 'BFC_MARKET_INFLUENCE', 'BFC-Influence from the market'
        BFC_REFUSING_TO_PAY = 'BFC_REFUSING_TO_PAY', 'BFC-Refusing to pay'
        BUSINESS_POORLY = 'BUSINESS_POORLY', 'Business performing Poorly'
        CLOSED_BUSINESS = 'CLOSED_BUSINESS', 'Closed Business'
        CUSTOMER_RELOCATED = 'CUSTOMER_RELOCATED', 'Customer Relocated'
        CUSTOMER_SICK = 'CUSTOMER_SICK', 'Customer Sick Or temporarily Incapacitated'
        FAMILY_SICKNESS = 'FAMILY_SICKNESS', 'Death and/or sickness in the family'
        DELAYED_PAYMENTS = 'DELAYED_PAYMENTS', 'Delayed Payments by customers/Paid by cheque'
        NATURAL_DISASTER = 'NATURAL_DISASTER', 'Environmental/Natural disaster'
        FIRES = 'FIRES', 'Fires'
        MARKET_DISRUPTION = 'MARKET_DISRUPTION', 'Market or Business Disruption'
        POLITICAL_VIOLENCE = 'POLITICAL_VIOLENCE', 'Political Violence'
        THEFT = 'THEFT', 'Theft-Proof of OB number'
        TRAFFIC_DISRUPTION = 'TRAFFIC_DISRUPTION', 'Traffic disruption'
        WRONG_STOCK = 'WRONG_STOCK', 'Wrong Stock Purchased'

    class DisbMethod(models.TextChoices):
        MPESA   = 'MPESA',   'M-Pesa B2C'
        BANK    = 'BANK',    'Bank Transfer'
        CASH    = 'CASH',    'Cash'

    class ApplicationMode(models.TextChoices):
        ONLINE  = 'ONLINE',  'Online'
        OFFLINE = 'OFFLINE', 'Offline (Physical)'
        USSD    = 'USSD',    'USSD'

    # Identifiers
    loan_id   = models.CharField(max_length=20, unique=True, editable=False)
    transcode = models.CharField(max_length=30, blank=True)

    # Relations
    customer  = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='loans')
    product   = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='loans')
    branch    = models.ForeignKey('branches.Branch', on_delete=models.PROTECT, related_name='loans')
    loan_officer   = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='lo_loans')
    credit_officer = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='co_loans')

    # Financials
    principal       = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('1'))])
    interest_rate   = models.DecimalField(max_digits=5, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    initiation_fee  = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    penalty_amount  = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount    = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_paid      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance         = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Terms
    tenure_days     = models.IntegerField()
    disbursement_method = models.CharField(max_length=10, choices=DisbMethod.choices, default=DisbMethod.MPESA)
    application_mode    = models.CharField(max_length=10, choices=ApplicationMode.choices, default=ApplicationMode.OFFLINE)

    # Dates
    disbursed_at  = models.DateTimeField(null=True, blank=True)
    due_date      = models.DateField(null=True, blank=True)
    closed_at     = models.DateTimeField(null=True, blank=True)

    # Workflow
    status          = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    verified_by     = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_loans')
    verified_at     = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, help_text='Notes from verification team about document checks')
    approved_by     = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_loans')
    approved_at     = models.DateTimeField(null=True, blank=True)
    disbursed_by    = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='disbursed_loans')
    disbursed_at    = models.DateTimeField(null=True, blank=True)
    default_reason  = models.CharField(max_length=30, choices=DefaultReason.choices, blank=True, null=True, help_text='Reason for loan default')
    rejection_reason = models.TextField(blank=True)
    notes           = models.TextField(blank=True)

    # ── Arrears & tier pricing ──────────────────────────────────────────────
    arrears_count   = models.IntegerField(default=0,
                      help_text='Consecutive missed repayments — triggers 21% rate at 3')
    effective_rate  = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                      help_text='Actual rate applied (tier / arrears override)')
    processing_fee  = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                      help_text='Processing fee: KES 500 first loan, KES 300 repeat')
    is_first_loan   = models.BooleanField(default=True,
                      help_text='True if first loan — determines KES 500 vs 300 fee')

    # M-Pesa
    mpesa_conversation_id = models.CharField(max_length=80, blank=True)
    mpesa_receipt         = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ql_loans'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.loan_id} — {self.customer.full_name} — KES {self.principal}'

    def save(self, *args, **kwargs):
        if not self.loan_id:
            from django.utils.timezone import now
            count = Loan.objects.count() + 1
            self.loan_id = f'QL-L{str(count).zfill(4)}'
        
        # BIASHARA product interest calculation
        if self.product and self.product.name == 'BIASHARA':
            weeks = self.tenure_days / 7
            base_rate = 20
            additional_weeks = weeks - 4
            if additional_weeks > 0:
                self.interest_rate = base_rate + (additional_weeks * 5)
            else:
                self.interest_rate = base_rate
        
        # Recalculate totals
        self.interest_amount = self.principal * (self.interest_rate / 100)
        self.total_amount = self.principal + self.interest_amount + self.initiation_fee
        self.balance = self.total_amount + self.penalty_amount - self.total_paid
        super().save(*args, **kwargs)

    def calculate_tamba_penalty(self, days_overdue):
        """
        TAMBA product penalty calculation:
        - Days 1-14: 2.5% penalty on outstanding amount (one-time)
        - Days 15-30: 5% penalty on outstanding amount (one-time)
        """
        if not self.product or self.product.name != 'TAMBA':
            return 0
        
        from decimal import Decimal
        outstanding = self.balance
        
        if days_overdue <= 14:
            penalty = outstanding * Decimal('0.025')  # 2.5% one-time
        elif days_overdue <= 30:
            penalty = outstanding * Decimal('0.05')   # 5% one-time
        else:
            penalty = outstanding * Decimal('0.05')   # 5% one-time (no additional penalty after 30 days)
        
        return penalty


class RepaymentSchedule(models.Model):
    """Installment schedule for a loan."""
    loan        = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='schedules')
    installment = models.IntegerField()
    due_date    = models.DateField()
    amount_due  = models.DecimalField(max_digits=14, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_paid     = models.BooleanField(default=False)
    paid_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ql_repayment_schedules'
        ordering = ['installment']


class WeeklyLoanConfig(models.Model):
    """
    Configuration for the weekly microfinance product.
    First-time limit is 5,000 KES, adjustable by HOP/Admin/GM/BDM.
    Rate: 20% per month (5% per week).
    Tenures: 4, 6, or 8 weeks.
    """
    branch          = models.OneToOneField('branches.Branch',
                        on_delete=models.CASCADE, related_name='weekly_loan_config')
    first_loan_limit= models.DecimalField(max_digits=10, decimal_places=2, default=5000,
                        help_text='Max amount for a first-time borrower in this branch')
    weekly_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=5.00,
                        help_text='Weekly interest rate as % (5% = 20%/month)')
    allowed_weeks   = models.JSONField(default=list,
                        help_text='Allowed loan durations e.g. [4, 6, 8]')
    is_active       = models.BooleanField(default=True)
    updated_by      = models.ForeignKey('accounts.User',
                        on_delete=models.SET_NULL, null=True, blank=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ql_weekly_loan_config'

    def __str__(self):
        return f'Weekly config — {self.branch.name}'

    def save(self, *args, **kwargs):
        if not self.allowed_weeks:
            self.allowed_weeks = [4, 6, 8]
        super().save(*args, **kwargs)
