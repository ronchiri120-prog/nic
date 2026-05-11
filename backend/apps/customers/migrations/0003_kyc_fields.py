from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("customers", "0002_kycdocument")]
    operations = [
        migrations.AddField(model_name="customer", name="county",
            field=models.CharField(blank=True, max_length=60)),
        migrations.AddField(model_name="customer", name="sub_county",
            field=models.CharField(blank=True, max_length=60)),
        migrations.AddField(model_name="customer", name="village",
            field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="customer", name="marital_status",
            field=models.CharField(blank=True, max_length=12,
                choices=[("SINGLE","Single"),("MARRIED","Married"),("DIVORCED","Divorced"),("WIDOWED","Widowed")])),
        migrations.AddField(model_name="customer", name="dependants",
            field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="customer", name="next_of_kin",
            field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="customer", name="next_of_kin_phone",
            field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name="customer", name="next_of_kin_relation",
            field=models.CharField(blank=True, max_length=60)),
        migrations.AddField(model_name="customer", name="employer_phone",
            field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name="customer", name="employer_address",
            field=models.TextField(blank=True)),
        migrations.AddField(model_name="customer", name="payslip_date",
            field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="customer", name="net_salary",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
    ]
