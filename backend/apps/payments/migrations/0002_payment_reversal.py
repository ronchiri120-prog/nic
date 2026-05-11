from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]
    operations = [
        migrations.AddField(model_name="payment", name="is_reversed",
            field=models.BooleanField(default=False)),
        migrations.AddField(model_name="payment", name="reversal_reason",
            field=models.TextField(blank=True)),
        migrations.AddField(model_name="payment", name="reversed_at",
            field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="payment", name="reversed_by",
            field=models.ForeignKey(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reversed_payments",
                to="accounts.user")),
    ]
