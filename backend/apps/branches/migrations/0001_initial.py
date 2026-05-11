from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=80, unique=True)),
                ('code', models.CharField(max_length=10, unique=True)),
            ],
            options={'db_table': 'ql_regions'},
        ),
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=10, unique=True)),
                ('region', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='branches', to='branches.region')),
                ('address', models.TextField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True)),
                ('disb_target', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('active_customer_target', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'ql_branches', 'ordering': ['name']},
        ),
    ]
