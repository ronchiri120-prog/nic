from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('branches', '0001_initial'),
        ('auth', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('password', models.CharField(max_length=128)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('is_superuser', models.BooleanField(default=False)),
                ('email', models.EmailField(unique=True)),
                ('full_name', models.CharField(max_length=120)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('role', models.CharField(
                    choices=[
                        ('SUPER_ADMIN','Super Admin'),('BRANCH_MANAGER','Branch Manager'),
                        ('LOAN_OFFICER','Loan Officer'),('CREDIT_OFFICER','Credit Officer'),
                        ('COLLECTIONS','Collections Agent'),('ACCOUNTANT','Accountant'),
                        ('BDO','Business Development Officer'),('READ_ONLY','Read Only'),
                    ],
                    default='READ_ONLY', max_length=20)),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff', to='branches.branch')),
                ('staff_id', models.CharField(blank=True, max_length=20, unique=True)),
                ('profile_pic', models.ImageField(blank=True, null=True, upload_to='staff/')),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('disbursement_target', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('groups', models.ManyToManyField(blank=True, related_name='user_set', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='user_set', to='auth.permission')),
            ],
            options={'db_table': 'ql_users', 'ordering': ['full_name']},
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.user')),
                ('action', models.CharField(max_length=200)),
                ('model_name', models.CharField(max_length=80)),
                ('object_id', models.CharField(blank=True, max_length=80)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'ql_audit_logs', 'ordering': ['-created_at']},
        ),
    ]
