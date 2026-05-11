from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0001_initial'),
        ('branches', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('uid', models.CharField(editable=False, max_length=20, unique=True)),
                ('first_name', models.CharField(max_length=80)),
                ('last_name', models.CharField(max_length=80)),
                ('national_id', models.CharField(max_length=20, unique=True)),
                ('gender', models.CharField(choices=[('M','Male'),('F','Female'),('O','Other')], default='M', max_length=1)),
                ('dob', models.DateField(blank=True, null=True)),
                ('phone', models.CharField(max_length=20)),
                ('phone2', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True)),
                ('address', models.TextField(blank=True)),
                ('id_front', models.ImageField(blank=True, null=True, upload_to='kyc/id/')),
                ('id_back', models.ImageField(blank=True, null=True, upload_to='kyc/id/')),
                ('photo', models.ImageField(blank=True, null=True, upload_to='kyc/photos/')),
                ('employer', models.CharField(blank=True, max_length=120)),
                ('monthly_income', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('employment_type', models.CharField(blank=True, max_length=40)),
                ('guarantor_name', models.CharField(blank=True, max_length=120)),
                ('guarantor_phone', models.CharField(blank=True, max_length=20)),
                ('guarantor_id', models.CharField(blank=True, max_length=20)),
                ('guarantor_relation', models.CharField(blank=True, max_length=60)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='customers', to='branches.branch')),
                ('loan_officer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_customers', to='accounts.user')),
                ('loan_limit', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('credit_score', models.IntegerField(default=0)),
                ('status', models.CharField(choices=[('ACTIVE','Active'),('DORMANT','Dormant'),('BLACKLISTED','Blacklisted'),('DECEASED','Deceased')], default='ACTIVE', max_length=15)),
                ('blacklist_reason', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'ql_customers', 'ordering': ['-created_at']},
        ),
    ]
