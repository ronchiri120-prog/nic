from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('loans',    '0003_loan_arrears'),
        ('branches', '0003_add_submarket'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WeeklyLoanConfig',
            fields=[
                ('id',              models.BigAutoField(primary_key=True)),
                ('first_loan_limit',models.DecimalField(max_digits=10, decimal_places=2, default=5000)),
                ('weekly_rate',     models.DecimalField(max_digits=5,  decimal_places=2, default=5.00)),
                ('allowed_weeks',   models.JSONField(default=list)),
                ('is_active',       models.BooleanField(default=True)),
                ('updated_at',      models.DateTimeField(auto_now=True)),
                ('branch',          models.OneToOneField('branches.Branch',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='weekly_loan_config')),
                ('updated_by',      models.ForeignKey(settings.AUTH_USER_MODEL,
                    on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True)),
            ],
            options={'db_table': 'ql_weekly_loan_config'},
        ),
        # Add weekly-specific fields to Loan
        migrations.AddField('Loan', 'weeks',
            models.IntegerField(null=True, blank=True,
                help_text='Loan duration in weeks (4, 6, or 8) for weekly products')),
        migrations.AddField('Loan', 'weekly_installment',
            models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                help_text='Calculated weekly repayment amount')),
        migrations.AddField('Loan', 'is_weekly',
            models.BooleanField(default=False, help_text='True for weekly repayment schedule')),
        migrations.AddField('Loan', 'next_due_date',
            models.DateField(null=True, blank=True, help_text='Next repayment due date')),
        migrations.AddField('Loan', 'last_payment_date',
            models.DateField(null=True, blank=True, help_text='Date of most recent payment')),
        migrations.AddField('Loan', 'mpesa_disburse_code',
            models.CharField(max_length=30, blank=True,
                help_text='M-Pesa transaction code for disbursement')),
    ]
