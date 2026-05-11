from django.db import migrations

# Documents app has no database models — generates HTML from other apps' data.
class Migration(migrations.Migration):
    initial      = True
    dependencies = []
    operations   = []
