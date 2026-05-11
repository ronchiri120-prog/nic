from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [("loans", "0002_product_fees")]
    operations = [
        migrations.AddField(model_name="loan", name="arrears_count",
            field=models.IntegerField(default=0,
                help_text="Consecutive missed repayments — triggers rate to 21% at 3")),
        migrations.AddField(model_name="loan", name="effective_rate",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True,
                help_text="Actual rate applied (may differ from product default due to tier)")),
        migrations.AddField(model_name="loan", name="processing_fee",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=10,
                help_text="Processing fee charged on this loan")),
        migrations.AddField(model_name="loan", name="is_first_loan",
            field=models.BooleanField(default=True,
                help_text="True if this is the customer's first loan with QuickLender")),
    ]
