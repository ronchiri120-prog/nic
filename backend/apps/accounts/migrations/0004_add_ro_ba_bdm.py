"""Add RO, BA, BDM role choices — data migration only, no schema change"""
from django.db import migrations


class Migration(migrations.Migration):
    """
    No schema change needed — Role is a CharField with TextChoices.
    Django TextChoices are enforced in Python only; DB stores plain strings.
    This migration documents the addition of RO, BA, BDM roles.
    """
    dependencies = [('accounts', '0003_add_hop_gm')]
    operations = []  # No DB changes needed for TextChoices
