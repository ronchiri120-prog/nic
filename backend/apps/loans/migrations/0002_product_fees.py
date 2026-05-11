from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [("loans", "0001_initial")]
    operations = [
        migrations.AddField(model_name="loanproduct", name="first_loan_fee",
            field=models.DecimalField(decimal_places=2, default=Decimal("500"), max_digits=10,
                help_text="Processing fee for first-time borrowers (KES 500)")),
        migrations.AddField(model_name="loanproduct", name="repeat_loan_fee",
            field=models.DecimalField(decimal_places=2, default=Decimal("300"), max_digits=10,
                help_text="Processing fee for repeat borrowers (KES 300)")),
        migrations.AddField(model_name="loanproduct", name="rate_silver",
            field=models.DecimalField(decimal_places=2, default=Decimal("20"), max_digits=5,
                help_text="Silver tier rate — standard (20%)")),
        migrations.AddField(model_name="loanproduct", name="rate_gold",
            field=models.DecimalField(decimal_places=2, default=Decimal("18"), max_digits=5,
                help_text="Gold tier rate — good repayors (18%)")),
        migrations.AddField(model_name="loanproduct", name="rate_platinum",
            field=models.DecimalField(decimal_places=2, default=Decimal("16"), max_digits=5,
                help_text="Platinum tier rate — excellent clients (16%)")),
        migrations.AddField(model_name="loanproduct", name="rate_arrears",
            field=models.DecimalField(decimal_places=2, default=Decimal("21"), max_digits=5,
                help_text="Arrears penalty rate — 3+ missed repayments (21%)")),
    ]
