from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("accounts",  "0001_initial"),
        ("branches",  "0001_initial"),
        ("customers", "0001_initial"),
        ("loans",     "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="LoanGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("group_id",   models.CharField(editable=False, max_length=20, unique=True)),
                ("name",       models.CharField(max_length=120)),
                ("branch",     models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="loan_groups", to="branches.branch")),
                ("loan_officer",models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="managed_groups", to="accounts.user")),
                ("chairperson", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chaired_groups", to="customers.customer")),
                ("secretary",   models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="secretary_groups", to="customers.customer")),
                ("status",      models.CharField(choices=[("ACTIVE","Active"),("DORMANT","Dormant"),("DISSOLVED","Dissolved")], default="ACTIVE", max_length=12)),
                ("meeting_day", models.CharField(blank=True, max_length=20)),
                ("meeting_location", models.TextField(blank=True)),
                ("max_members", models.IntegerField(default=30)),
                ("group_fund",  models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("notes",       models.TextField(blank=True)),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ql_loan_groups", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="GroupMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("group",     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="groups.loangroup")),
                ("customer",  models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="group_memberships", to="customers.customer")),
                ("role",      models.CharField(choices=[("MEMBER","Member"),("CHAIRPERSON","Chairperson"),("SECRETARY","Secretary"),("TREASURER","Treasurer")], default="MEMBER", max_length=14)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=True)),
                ("shares",    models.IntegerField(default=1)),
            ],
            options={"db_table": "ql_group_memberships", "unique_together": {("group","customer")}},
        ),
        migrations.AddField(
            model_name="groupmembership",
            name="guarantees",
            field=models.ManyToManyField(blank=True, related_name="guaranteed_by", to="customers.customer"),
        ),
        migrations.CreateModel(
            name="GroupLoan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("group_loan_id", models.CharField(editable=False, max_length=20, unique=True)),
                ("group",         models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="loans", to="groups.loangroup")),
                ("product",       models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="loans.loanproduct")),
                ("total_amount",  models.DecimalField(decimal_places=2, max_digits=14)),
                ("interest_rate", models.DecimalField(decimal_places=2, max_digits=5)),
                ("tenure_days",   models.IntegerField()),
                ("status",        models.CharField(choices=[("PENDING","Pending Approval"),("APPROVED","Approved"),("ACTIVE","Active"),("CLOSED","Closed"),("DEFAULT","Default")], default="PENDING", max_length=12)),
                ("approved_by",   models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="accounts.user")),
                ("approved_at",   models.DateTimeField(blank=True, null=True)),
                ("disbursed_at",  models.DateTimeField(blank=True, null=True)),
                ("due_date",      models.DateField(blank=True, null=True)),
                ("notes",         models.TextField(blank=True)),
                ("created_at",    models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ql_group_loans", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="GroupLoanShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("group_loan",  models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shares", to="groups.grouploan")),
                ("member",      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="loan_shares", to="groups.groupmembership")),
                ("amount",      models.DecimalField(decimal_places=2, max_digits=14)),
                ("total_due",   models.DecimalField(decimal_places=2, max_digits=14)),
                ("total_paid",  models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("balance",     models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("individual_loan", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="group_share", to="loans.loan")),
            ],
            options={"db_table": "ql_group_loan_shares"},
        ),
    ]
