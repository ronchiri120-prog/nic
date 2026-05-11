"""payments/models.py"""
from django.db import models
from decimal import Decimal


class Payment(models.Model):
    class Method(models.TextChoices):
        MPESA  = 'MPESA',  'M-Pesa'
        BANK   = 'BANK',   'Bank Transfer'
        CASH   = 'CASH',   'Cash'

    class PaymentType(models.TextChoices):
        FULL              = 'FULL',              'Full Payment'
        PARTIAL           = 'PARTIAL',           'Partial Payment'
        PENALTY           = 'PENALTY',           'Penalty'
        FIRST_TIME_FEE    = 'FIRST_TIME_FEE',    'First-time Applicant Fee'
        REPEAT_FEE        = 'REPEAT_FEE',        'Repeat Customer Processing Fee'

    ref        = models.CharField(max_length=30, unique=True, editable=False)
    loan       = models.ForeignKey('loans.Loan', on_delete=models.PROTECT, related_name='payments')
    amount     = models.DecimalField(max_digits=14, decimal_places=2, validators=[])
    method     = models.CharField(max_length=10, choices=Method.choices)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.PARTIAL)
    mpesa_ref  = models.CharField(max_length=30, blank=True)
    phone      = models.CharField(max_length=20, blank=True)
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    notes      = models.TextField(blank=True)
    paid_at    = models.DateTimeField()
    # Reversal tracking
    is_reversed     = models.BooleanField(default=False)
    reversal_reason = models.TextField(blank=True)
    reversed_by     = models.ForeignKey('accounts.User', null=True, blank=True,
                        on_delete=models.SET_NULL, related_name='reversed_payments')
    reversed_at     = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ql_payments'
        ordering = ['-paid_at']

    def __str__(self):
        return f'{self.ref} — KES {self.amount}'

    def save(self, *args, **kwargs):
        if not self.ref:
            count = Payment.objects.count() + 1
            self.ref = f'PMT-{str(count).zfill(4)}'
        super().save(*args, **kwargs)
        # Update loan balance
        self._update_loan()

    def _update_loan(self):
        loan = self.loan
        from django.db.models import Sum
        total_paid = Payment.objects.filter(loan=loan).aggregate(s=Sum('amount'))['s'] or 0
        loan.total_paid = total_paid
        loan.balance = loan.total_amount + loan.penalty_amount - total_paid
        if loan.balance <= 0:
            from django.utils import timezone
            loan.status = 'CLOSED'
            loan.closed_at = timezone.now()
        loan.save(update_fields=['total_paid', 'balance', 'status', 'closed_at'])


class MpesaTransaction(models.Model):
    """Logs all raw M-Pesa API transactions."""
    class TxnType(models.TextChoices):
        B2C = 'B2C', 'B2C Disbursement'
        STK = 'STK', 'STK Push Collection'
        C2B = 'C2B', 'C2B Collection'

    class TxnStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED  = 'FAILED',  'Failed'

    loan                = models.ForeignKey('loans.Loan', on_delete=models.SET_NULL, null=True, blank=True)
    txn_type            = models.CharField(max_length=5, choices=TxnType.choices)
    phone               = models.CharField(max_length=20)
    amount              = models.DecimalField(max_digits=14, decimal_places=2)
    mpesa_receipt       = models.CharField(max_length=30, blank=True)
    conversation_id     = models.CharField(max_length=80, blank=True)
    originator_id       = models.CharField(max_length=80, blank=True)
    status              = models.CharField(max_length=10, choices=TxnStatus.choices, default=TxnStatus.PENDING)
    result_desc         = models.TextField(blank=True)
    raw_request         = models.JSONField(default=dict, blank=True)
    raw_response        = models.JSONField(default=dict, blank=True)
    initiated_at        = models.DateTimeField(auto_now_add=True)
    completed_at        = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ql_mpesa_transactions'
        ordering = ['-initiated_at']
