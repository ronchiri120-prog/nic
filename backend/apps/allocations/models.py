from django.db import models

class Allocation(models.Model):
    agent       = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="allocations")
    loan        = models.ForeignKey("loans.Loan", on_delete=models.CASCADE, related_name="allocations")
    branch      = models.ForeignKey("branches.Branch", on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="given_allocations")
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = "ql_allocations"
        unique_together = ["agent", "loan"]

    def __str__(self):
        return f"{self.agent.full_name} => {self.loan.loan_id}"
