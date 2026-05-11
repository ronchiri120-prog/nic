"""
accounting/models.py
Full double-entry General Ledger for QuickLender.

Chart of Accounts follows standard MFI structure:
  1xxx — Assets
  2xxx — Liabilities
  3xxx — Equity
  4xxx — Income
  5xxx — Expenses
  6xxx — Contra / provisions
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class AccountType(models.TextChoices):
    ASSET     = 'ASSET',     'Asset'
    LIABILITY = 'LIABILITY', 'Liability'
    EQUITY    = 'EQUITY',    'Equity'
    INCOME    = 'INCOME',    'Income'
    EXPENSE   = 'EXPENSE',   'Expense'


class Account(models.Model):
    """Chart of Accounts — every GL account."""
    code        = models.CharField(max_length=10, unique=True)
    name        = models.CharField(max_length=120)
    account_type= models.CharField(max_length=12, choices=AccountType.choices)
    parent      = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    is_control  = models.BooleanField(default=False, help_text='Control account — no direct posting')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ql_gl_accounts'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'

    @property
    def balance(self):
        """Current balance: debits - credits for asset/expense, credits - debits for others."""
        from django.db.models import Sum
        entries = self.journal_entries.aggregate(
            debits=Sum('debit_amount'),
            credits=Sum('credit_amount'),
        )
        d = entries['debits']  or Decimal('0')
        c = entries['credits'] or Decimal('0')
        if self.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            return d - c
        return c - d


class JournalEntry(models.Model):
    """A balanced journal entry (header)."""
    class Status(models.TextChoices):
        DRAFT    = 'DRAFT',    'Draft'
        POSTED   = 'POSTED',   'Posted'
        REVERSED = 'REVERSED', 'Reversed'

    reference   = models.CharField(max_length=30, unique=True, editable=False)
    narration   = models.CharField(max_length=255)
    date        = models.DateField()
    status      = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    source_type = models.CharField(max_length=40, blank=True, help_text='loan, payment, manual, penalty')
    source_id   = models.PositiveIntegerField(null=True, blank=True)
    reversal_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reversals')
    created_by  = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL)
    posted_at   = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ql_journal_entries'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.reference} | {self.narration}'

    def save(self, *args, **kwargs):
        if not self.reference:
            count = JournalEntry.objects.count() + 1
            self.reference = f'JE-{str(count).zfill(5)}'
        super().save(*args, **kwargs)

    @property
    def is_balanced(self):
        from django.db.models import Sum
        totals = self.lines.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
        return (totals['d'] or 0) == (totals['c'] or 0)

    def post(self, user=None):
        from django.utils import timezone
        if not self.is_balanced:
            raise ValueError('Journal entry is not balanced — cannot post')
        self.status    = self.Status.POSTED
        self.posted_at = timezone.now()
        if user:
            self.created_by = user
        self.save()

    def reverse(self, user=None, narration=''):
        """Create a reversing entry."""
        from django.utils import timezone
        rev = JournalEntry.objects.create(
            narration   = narration or f'Reversal of {self.reference}',
            date        = timezone.now().date(),
            status      = JournalEntry.Status.POSTED,
            source_type = 'reversal',
            source_id   = self.id,
            reversal_of = self,
            created_by  = user,
            posted_at   = timezone.now(),
        )
        for line in self.lines.all():
            JournalLine.objects.create(
                entry         = rev,
                account       = line.account,
                debit_amount  = line.credit_amount,
                credit_amount = line.debit_amount,
                description   = line.description,
            )
        self.status = JournalEntry.Status.REVERSED
        self.save()
        return rev


class JournalLine(models.Model):
    """One line of a journal entry (debit or credit)."""
    entry         = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account       = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_entries')
    debit_amount  = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    credit_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0'))
    description   = models.CharField(max_length=200, blank=True)
    branch        = models.ForeignKey('branches.Branch', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'ql_journal_lines'

    def __str__(self):
        if self.debit_amount:
            return f'DR {self.account.code} {self.debit_amount}'
        return f'CR {self.account.code} {self.credit_amount}'


class FiscalPeriod(models.Model):
    """Monthly/quarterly accounting periods."""
    class Status(models.TextChoices):
        OPEN   = 'OPEN',   'Open'
        CLOSED = 'CLOSED', 'Closed'

    name       = models.CharField(max_length=50)   # e.g. "March 2026"
    start_date = models.DateField()
    end_date   = models.DateField()
    status     = models.CharField(max_length=8, choices=Status.choices, default=Status.OPEN)
    closed_by  = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)
    closed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ql_fiscal_periods'
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.name} [{self.status}]'
