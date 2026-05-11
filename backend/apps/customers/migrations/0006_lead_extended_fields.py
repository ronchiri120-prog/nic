"""Add extended profile fields to Lead model for detail/convert step"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('customers', '0005_lead')]

    operations = [
        migrations.AddField('Lead', 'phone2',               models.CharField(max_length=20,  blank=True)),
        migrations.AddField('Lead', 'marital_status',       models.CharField(max_length=12,  blank=True)),
        migrations.AddField('Lead', 'dob',                  models.DateField(null=True, blank=True)),
        migrations.AddField('Lead', 'home_address',         models.TextField(blank=True)),
        migrations.AddField('Lead', 'business_name',        models.CharField(max_length=120, blank=True)),
        migrations.AddField('Lead', 'monthly_income',       models.DecimalField(max_digits=12, decimal_places=2, default=0)),
        migrations.AddField('Lead', 'next_of_kin',          models.CharField(max_length=120, blank=True)),
        migrations.AddField('Lead', 'next_of_kin_phone',    models.CharField(max_length=20,  blank=True)),
        migrations.AddField('Lead', 'next_of_kin_relation', models.CharField(max_length=60,  blank=True)),
        migrations.AddField('Lead', 'guarantor_name',       models.CharField(max_length=120, blank=True)),
        migrations.AddField('Lead', 'guarantor_phone',      models.CharField(max_length=20,  blank=True)),
        migrations.AddField('Lead', 'guarantor_id',         models.CharField(max_length=20,  blank=True)),
        migrations.AddField('Lead', 'guarantor_relation',   models.CharField(max_length=60,  blank=True)),
        migrations.AddField('Lead', 'guarantor_address',    models.TextField(blank=True)),
    ]
