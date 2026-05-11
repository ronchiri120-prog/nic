from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("customers", "0001_initial"), ("accounts", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="KYCDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="customers.customer")),
                ("category", models.CharField(max_length=20, choices=[
                    ("ID_FRONT","National ID Front"),("ID_BACK","National ID Back"),
                    ("PASSPORT_PHOTO","Passport Photo"),("PAYSLIP","Payslip"),
                    ("BANK_STATEMENT","Bank Statement"),("LOGBOOK","Logbook"),
                    ("TITLE_DEED","Title Deed"),("GUARANTOR_ID","Guarantor ID"),("OTHER","Other"),
                ])),
                ("s3_key",       models.CharField(max_length=400)),
                ("filename",     models.CharField(max_length=200)),
                ("content_type", models.CharField(max_length=50)),
                ("file_size",    models.PositiveIntegerField(default=0)),
                ("status",       models.CharField(choices=[("PENDING","Pending Review"),("APPROVED","Approved"),("REJECTED","Rejected")], default="PENDING", max_length=10)),
                ("reviewed_by",  models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="accounts.user")),
                ("notes",        models.TextField(blank=True)),
                ("uploaded_at",  models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ql_kyc_documents", "ordering": ["-uploaded_at"]},
        ),
    ]
