"""
groups/models.py — Group / Chama Lending
Supports joint liability groups where members guarantee each other.
"""
from django.db import models
from decimal import Decimal


class LoanGroup(models.Model):
    """A chama / self-help group that borrows collectively."""
    class Status(models.TextChoices):
        ACTIVE   = "ACTIVE",   "Active"
        DORMANT  = "DORMANT",  "Dormant"
        DISSOLVED= "DISSOLVED","Dissolved"

    group_id    = models.CharField(max_length=20, unique=True, editable=False)
    name        = models.CharField(max_length=120)
    branch      = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="loan_groups")
    loan_officer= models.ForeignKey("accounts.User",   on_delete=models.SET_NULL, null=True, related_name="managed_groups")
    chairperson = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, null=True, related_name="chaired_groups")
    secretary   = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="secretary_groups")
    status      = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    meeting_day = models.CharField(max_length=20, blank=True)   # e.g. "Every Tuesday"
    meeting_location = models.TextField(blank=True)
    max_members = models.IntegerField(default=30)
    group_fund  = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"), help_text="Group savings / guarantee fund")
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ql_loan_groups"
        ordering = ["name"]

    def __str__(self):
        return f"{self.group_id} — {self.name}"

    def save(self, *args, **kwargs):
        if not self.group_id:
            count = LoanGroup.objects.count() + 1
            self.group_id = f"GRP-{str(count).zfill(4)}"
        super().save(*args, **kwargs)

    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()

    @property
    def active_loans_count(self):
        return GroupLoan.objects.filter(group=self, status__in=["ACTIVE","APPROVED"]).count()


class GroupMembership(models.Model):
    """A customer's membership in a loan group."""
    class Role(models.TextChoices):
        MEMBER       = "MEMBER",      "Member"
        CHAIRPERSON  = "CHAIRPERSON", "Chairperson"
        SECRETARY    = "SECRETARY",   "Secretary"
        TREASURER    = "TREASURER",   "Treasurer"

    group      = models.ForeignKey(LoanGroup, on_delete=models.CASCADE, related_name="memberships")
    customer   = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="group_memberships")
    role       = models.CharField(max_length=14, choices=Role.choices, default=Role.MEMBER)
    joined_at  = models.DateTimeField(auto_now_add=True)
    is_active  = models.BooleanField(default=True)
    shares     = models.IntegerField(default=1, help_text="Number of group shares held")
    guarantees = models.ManyToManyField("customers.Customer", blank=True, related_name="guaranteed_by",
                                        help_text="Members this person guarantees")

    class Meta:
        db_table = "ql_group_memberships"
        unique_together = ["group", "customer"]

    def __str__(self):
        return f"{self.customer.full_name} @ {self.group.name} ({self.role})"


class GroupLoan(models.Model):
    """A loan made to a group, split across members."""
    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        ACTIVE   = "ACTIVE",   "Active"
        CLOSED   = "CLOSED",   "Closed"
        DEFAULT  = "DEFAULT",  "Default"

    group_loan_id = models.CharField(max_length=20, unique=True, editable=False)
    group         = models.ForeignKey(LoanGroup, on_delete=models.PROTECT, related_name="loans")
    product       = models.ForeignKey("loans.LoanProduct", on_delete=models.PROTECT)
    total_amount  = models.DecimalField(max_digits=14, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5,  decimal_places=2)
    tenure_days   = models.IntegerField()
    status        = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    approved_by   = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    approved_at   = models.DateTimeField(null=True, blank=True)
    disbursed_at  = models.DateTimeField(null=True, blank=True)
    due_date      = models.DateField(null=True, blank=True)
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ql_group_loans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.group_loan_id} — {self.group.name} KES {self.total_amount}"

    def save(self, *args, **kwargs):
        if not self.group_loan_id:
            count = GroupLoan.objects.count() + 1
            self.group_loan_id = f"GRP-L{str(count).zfill(4)}"
        super().save(*args, **kwargs)


class GroupLoanShare(models.Model):
    """Individual member's share of a group loan."""
    group_loan  = models.ForeignKey(GroupLoan, on_delete=models.CASCADE, related_name="shares")
    member      = models.ForeignKey(GroupMembership, on_delete=models.CASCADE, related_name="loan_shares")
    amount      = models.DecimalField(max_digits=14, decimal_places=2)
    total_due   = models.DecimalField(max_digits=14, decimal_places=2)
    total_paid  = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    balance     = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    individual_loan = models.OneToOneField("loans.Loan", on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name="group_share",
                                           help_text="Individual loan record created from this share")

    class Meta:
        db_table = "ql_group_loan_shares"

    def __str__(self):
        return f"{self.member.customer.full_name}: KES {self.amount} of {self.group_loan.group_loan_id}"
