from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = False
    dependencies = [
        ('branches', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='branch',
            name='manager',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='managed_branches',
                to='accounts.user',
            ),
        ),
    ]
