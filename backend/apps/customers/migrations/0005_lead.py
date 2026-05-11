"""Migration: Lead model + business/guarantor fields on Customer"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0004_client_tier'),
        ('branches',  '0003_add_submarket'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Lead model ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('id',            models.BigAutoField(primary_key=True)),
                ('lead_id',       models.CharField(max_length=20, unique=True, editable=False)),
                ('first_name',    models.CharField(max_length=80)),
                ('last_name',     models.CharField(max_length=80)),
                ('phone',         models.CharField(max_length=20)),
                ('national_id',   models.CharField(max_length=20, blank=True)),
                ('gender',        models.CharField(max_length=1,
                    choices=[('M','Male'),('F','Female'),('O','Other')], default='M')),
                ('business_category', models.CharField(max_length=100, blank=True)),
                ('business_location', models.CharField(max_length=200, blank=True)),
                ('submarket',     models.CharField(max_length=80, blank=True)),
                ('notes',         models.TextField(blank=True)),
                ('status',        models.CharField(max_length=15,
                    choices=[('NEW','New'),('CONTACTED','Contacted'),
                             ('QUALIFIED','Qualified'),('CONVERTED','Converted'),
                             ('LOST','Lost')],
                    default='NEW')),
                ('source',        models.CharField(max_length=40, blank=True,
                    choices=[('WALK_IN','Walk-in'),('REFERRAL','Referral'),
                             ('MARKETING','Marketing'),('SOCIAL','Social Media'),('OTHER','Other')],
                    default='WALK_IN')),
                ('branch',        models.ForeignKey('branches.Branch',
                    on_delete=django.db.models.deletion.PROTECT, related_name='leads')),
                ('created_by',    models.ForeignKey(settings.AUTH_USER_MODEL,
                    on_delete=django.db.models.deletion.SET_NULL, null=True,
                    related_name='leads_created')),
                ('assigned_to',   models.ForeignKey(settings.AUTH_USER_MODEL,
                    on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True,
                    related_name='leads_assigned')),
                ('converted_by',  models.ForeignKey(settings.AUTH_USER_MODEL,
                    on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True,
                    related_name='leads_converted')),
                ('converted_at',  models.DateTimeField(null=True, blank=True)),
                ('customer',      models.OneToOneField('customers.Customer',
                    on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True,
                    related_name='lead')),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'ql_leads', 'ordering': ['-created_at']},
        ),
        # ── Business fields on Customer ─────────────────────────────────────
        migrations.AddField('Customer', 'business_name',
            models.CharField(max_length=120, blank=True)),
        migrations.AddField('Customer', 'business_category',
            models.CharField(max_length=100, blank=True)),
        migrations.AddField('Customer', 'business_location',
            models.CharField(max_length=200, blank=True)),
        migrations.AddField('Customer', 'business_address',
            models.TextField(blank=True)),
        migrations.AddField('Customer', 'home_address',
            models.TextField(blank=True)),
        migrations.AddField('Customer', 'geo_lat',
            models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)),
        migrations.AddField('Customer', 'geo_lng',
            models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)),
        # ── Guarantor document fields ───────────────────────────────────────
        migrations.AddField('Customer', 'guarantor_id_front',
            models.ImageField(upload_to='kyc/guarantor/', null=True, blank=True)),
        migrations.AddField('Customer', 'guarantor_id_back',
            models.ImageField(upload_to='kyc/guarantor/', null=True, blank=True)),
        migrations.AddField('Customer', 'guarantor_passport',
            models.ImageField(upload_to='kyc/guarantor/', null=True, blank=True)),
        migrations.AddField('Customer', 'guarantor_address',
            models.TextField(blank=True)),
        migrations.AddField('Customer', 'guarantor_business_address',
            models.TextField(blank=True)),
    ]
