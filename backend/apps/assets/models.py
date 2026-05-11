from django.db import models

class Asset(models.Model):
    class Category(models.TextChoices):
        VEHICLE    = "VEHICLE",    "Motor Vehicle"
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
        LAND       = "LAND",       "Land/Property"
        OTHER      = "OTHER",      "Other"

    asset_id    = models.CharField(max_length=20, unique=True, editable=False)
    customer    = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="assets")
    loan        = models.ForeignKey("loans.Loan", on_delete=models.SET_NULL, null=True, blank=True, related_name="collateral")
    category    = models.CharField(max_length=15, choices=Category.choices)
    make        = models.CharField(max_length=60, blank=True)
    model       = models.CharField(max_length=60, blank=True)
    year        = models.IntegerField(null=True, blank=True)
    reg_number  = models.CharField(max_length=20, blank=True)
    color       = models.CharField(max_length=30, blank=True)
    valuation   = models.DecimalField(max_digits=14, decimal_places=2)
    valued_by   = models.CharField(max_length=100, blank=True)
    valued_at   = models.DateField(null=True, blank=True)
    logbook_no  = models.CharField(max_length=30, blank=True)
    notes       = models.TextField(blank=True)
    photo       = models.ImageField(upload_to="assets/", null=True, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ql_assets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.asset_id} — {self.make} {self.model} ({self.reg_number})"

    def save(self, *args, **kwargs):
        if not self.asset_id:
            count = Asset.objects.count() + 1
            self.asset_id = f"AST-{str(count).zfill(4)}"
        super().save(*args, **kwargs)

    @property
    def ltv(self):
        if self.loan and self.valuation:
            return round((float(self.loan.principal) / float(self.valuation)) * 100, 1)
        return 0
