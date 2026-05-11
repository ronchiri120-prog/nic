from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0001_initial'),
        ('branches', '0001_initial'),
        ('loans', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Allocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocations', to='accounts.user')),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocations', to='loans.loan')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='branches.branch')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='given_allocations', to='accounts.user')),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'db_table': 'ql_allocations'},
        ),
        migrations.AlterUniqueTogether(
            name='allocation',
            unique_together={('agent', 'loan')},
        ),
    ]
