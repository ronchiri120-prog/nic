from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("customers", "0003_kyc_fields")]
    operations = [
        migrations.AddField(model_name="customer", name="tier",
            field=models.CharField(
                choices=[("PLATINUM","Platinum — 16%"),("GOLD","Gold — 18%"),("SILVER","Silver — 20%")],
                default="SILVER", max_length=10)),
        migrations.AddField(model_name="customer", name="tier_updated_at",
            field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="customer", name="tier_notes",
            field=models.TextField(blank=True)),
        migrations.AddField(model_name="customer", name="total_loans_paid",
            field=models.IntegerField(default=0)),
    ]
