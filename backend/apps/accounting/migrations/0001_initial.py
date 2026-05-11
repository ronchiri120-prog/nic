from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("accounts", "0001_initial"),
        ("branches", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=10, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("account_type", models.CharField(
                    choices=[("ASSET","Asset"),("LIABILITY","Liability"),
                             ("EQUITY","Equity"),("INCOME","Income"),("EXPENSE","Expense")],
                    max_length=12)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="accounting.account")),
                ("description", models.TextField(blank=True)),
                ("is_active",  models.BooleanField(default=True)),
                ("is_control", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ql_gl_accounts", "ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="FiscalPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name",       models.CharField(max_length=50)),
                ("start_date", models.DateField()),
                ("end_date",   models.DateField()),
                ("status",     models.CharField(choices=[("OPEN","Open"),("CLOSED","Closed")], default="OPEN", max_length=8)),
                ("closed_by",  models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="accounts.user")),
                ("closed_at",  models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "ql_fiscal_periods", "ordering": ["-start_date"]},
        ),
        migrations.CreateModel(
            name="JournalEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("reference",   models.CharField(editable=False, max_length=30, unique=True)),
                ("narration",   models.CharField(max_length=255)),
                ("date",        models.DateField()),
                ("status",      models.CharField(choices=[("DRAFT","Draft"),("POSTED","Posted"),("REVERSED","Reversed")], default="DRAFT", max_length=12)),
                ("source_type", models.CharField(blank=True, max_length=40)),
                ("source_id",   models.PositiveIntegerField(blank=True, null=True)),
                ("reversal_of", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reversals", to="accounting.journalentry")),
                ("created_by",  models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="accounts.user")),
                ("posted_at",   models.DateTimeField(blank=True, null=True)),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ql_journal_entries", "ordering": ["-date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="JournalLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("entry",         models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="accounting.journalentry")),
                ("account",       models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journal_entries", to="accounting.account")),
                ("debit_amount",  models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=16)),
                ("credit_amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=16)),
                ("description",   models.CharField(blank=True, max_length=200)),
                ("branch",        models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="branches.branch")),
            ],
            options={"db_table": "ql_journal_lines"},
        ),
    ]
