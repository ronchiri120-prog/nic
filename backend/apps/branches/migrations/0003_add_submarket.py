from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("branches", "0002_add_manager")]
    operations = [
        migrations.AddField(model_name="branch", name="submarket",
            field=models.CharField(blank=True, max_length=80,
                help_text="Sub-market / territory e.g. Eastlands, Westlands")),
    ]
