from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_add_2fa")]
    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=__import__("django.db.models", fromlist=["CharField"]).CharField(
                choices=[
                    ("SUPER_ADMIN","Super Admin"),
                    ("BRANCH_MANAGER","Branch Manager"),
                    ("LOAN_OFFICER","Loan Officer"),
                    ("CREDIT_OFFICER","Credit Officer"),
                    ("COLLECTIONS","Collections Agent"),
                    ("ACCOUNTANT","Accountant"),
                    ("BDO","Business Development Officer"),
                    ("HOP","Head of Products"),
                    ("GM","General Manager"),
                    ("READ_ONLY","Read Only"),
                ],
                default="LOAN_OFFICER",
                max_length=20,
            ),
        ),
    ]
