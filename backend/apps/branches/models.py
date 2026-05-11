"""branches/models.py"""
from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=10, unique=True)
    manager = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_regions'
    )

    class Meta:
        db_table = 'ql_regions'

    def __str__(self):
        return self.name


class Branch(models.Model):
    class BranchType(models.TextChoices):
        BRANCH = 'BRANCH', 'Branch'
        HQ = 'HQ', 'Headquarters'

    name    = models.CharField(max_length=100)
    code    = models.CharField(max_length=10, unique=True)
    branch_type = models.CharField(
        max_length=10,
        choices=BranchType.choices,
        default=BranchType.BRANCH,
        help_text="Branch type: Regular Branch or Headquarters"
    )
    region  = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, related_name='branches')
    manager = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_branches'
    )
    submarket       = models.CharField(max_length=80, blank=True,
                          help_text="Sub-market / territory e.g. Eastlands, Westlands")
    address         = models.TextField(blank=True)
    phone           = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
    disb_target     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    active_customer_target = models.IntegerField(default=0)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ql_branches'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'

    @property
    def staff_count(self):
        return self.staff.filter(is_active=True).count()

    @property
    def active_loans_count(self):
        return self.loans.filter(status='ACTIVE').count()
