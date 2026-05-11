from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0001_initial'),
        ('loans', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('ref', models.CharField(editable=False, max_length=30, unique=True)),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='loans.loan')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('method', models.CharField(choices=[('MPESA','M-Pesa'),('BANK','Bank Transfer'),('CASH','Cash')], max_length=10)),
                ('payment_type', models.CharField(choices=[('FULL','Full Payment'),('PARTIAL','Partial Payment'),('PENALTY','Penalty')], default='PARTIAL', max_length=10)),
                ('mpesa_ref', models.CharField(blank=True, max_length=30)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('recorded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.user')),
                ('notes', models.TextField(blank=True)),
                ('paid_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'ql_payments', 'ordering': ['-paid_at']},
        ),
        migrations.CreateModel(
            name='MpesaTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('loan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='loans.loan')),
                ('txn_type', models.CharField(choices=[('B2C','B2C Disbursement'),('STK','STK Push Collection'),('C2B','C2B Collection')], max_length=5)),
                ('phone', models.CharField(max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('mpesa_receipt', models.CharField(blank=True, max_length=30)),
                ('conversation_id', models.CharField(blank=True, max_length=80)),
                ('originator_id', models.CharField(blank=True, max_length=80)),
                ('status', models.CharField(choices=[('PENDING','Pending'),('SUCCESS','Success'),('FAILED','Failed')], default='PENDING', max_length=10)),
                ('result_desc', models.TextField(blank=True)),
                ('raw_request', models.JSONField(blank=True, default=dict)),
                ('raw_response', models.JSONField(blank=True, default=dict)),
                ('initiated_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'db_table': 'ql_mpesa_transactions', 'ordering': ['-initiated_at']},
        ),
    ]
