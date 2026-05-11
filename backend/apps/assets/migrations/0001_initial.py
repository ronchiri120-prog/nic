from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('customers', '0001_initial'),
        ('loans', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('asset_id', models.CharField(editable=False, max_length=20, unique=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assets', to='customers.customer')),
                ('loan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='collateral', to='loans.loan')),
                ('category', models.CharField(choices=[('VEHICLE','Motor Vehicle'),('MOTORCYCLE','Motorcycle'),('LAND','Land/Property'),('OTHER','Other')], max_length=15)),
                ('make', models.CharField(blank=True, max_length=60)),
                ('model', models.CharField(blank=True, max_length=60)),
                ('year', models.IntegerField(blank=True, null=True)),
                ('reg_number', models.CharField(blank=True, max_length=20)),
                ('color', models.CharField(blank=True, max_length=30)),
                ('valuation', models.DecimalField(decimal_places=2, max_digits=14)),
                ('valued_by', models.CharField(blank=True, max_length=100)),
                ('valued_at', models.DateField(blank=True, null=True)),
                ('logbook_no', models.CharField(blank=True, max_length=30)),
                ('notes', models.TextField(blank=True)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='assets/')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'ql_assets', 'ordering': ['-created_at']},
        ),
    ]
