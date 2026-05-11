"""Add RM, Marketing Manager, Assistant, Surge Team, Collections Manager/Asst, HOP Asst, Asst BDM"""
from django.db import migrations

class Migration(migrations.Migration):
    """No DB schema change — TextChoices are Python-side only."""
    dependencies = [('accounts', '0004_add_ro_ba_bdm')]
    operations = []
