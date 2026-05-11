from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0001_initial'),
        ('branches', '0001_initial'),
        ('customers', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='LoanProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=80)),
                ('loan_type', models.CharField(choices=[('FA','Salary Advance (FA)'),('CC','Credit Check (CC)'),('LOGBOOK','Logbook Loan'),('IDC','IDC'),('EDC','EDC'),('CUSTOM','Custom')], max_length=10)),
                ('min_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('max_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('interest_rate', models.DecimalField(decimal_places=2, max_digits=5)),
                ('tenure_days', models.IntegerField()),
                ('penalty_rate', models.DecimalField(decimal_places=2, default=Decimal('0.5'), max_digits=5)),
                ('initiation_fee', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'db_table': 'ql_loan_products'},
        ),
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('loan_id', models.CharField(editable=False, max_length=20, unique=True)),
                ('transcode', models.CharField(blank=True, max_length=30)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loans', to='customers.customer')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loans', to='loans.loanproduct')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loans', to='branches.branch')),
                ('loan_officer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lo_loans', to='accounts.user')),
                ('credit_officer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='co_loans', to='accounts.user')),
                ('principal', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal('1'))])),
                ('interest_rate', models.DecimalField(decimal_places=2, max_digits=5)),
                ('interest_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('initiation_fee', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('penalty_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('total_paid', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('balance', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('tenure_days', models.IntegerField()),
                ('disbursement_method', models.CharField(choices=[('MPESA','M-Pesa B2C'),('BANK','Bank Transfer'),('CASH','Cash')], default='MPESA', max_length=10)),
                ('application_mode', models.CharField(choices=[('ONLINE','Online'),('OFFLINE','Offline (Physical)'),('USSD','USSD')], default='OFFLINE', max_length=10)),
                ('disbursed_at', models.DateTimeField(blank=True, null=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING','Pending Approval'),('APPROVED','Approved'),('DISBURSED','Disbursed'),('ACTIVE','Active'),('CLOSED','Closed'),('DEFAULT','Default'),('WRITTEN_OFF','Written Off'),('REJECTED','Rejected')], default='PENDING', max_length=15)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_loans', to='accounts.user')),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('mpesa_conversation_id', models.CharField(blank=True, max_length=80)),
                ('mpesa_receipt', models.CharField(blank=True, max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'ql_loans', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='RepaymentSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='loans.loan')),
                ('installment', models.IntegerField()),
                ('due_date', models.DateField()),
                ('amount_due', models.DecimalField(decimal_places=2, max_digits=14)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('is_paid', models.BooleanField(default=False)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'db_table': 'ql_repayment_schedules', 'ordering': ['installment']},
        ),
    ]
