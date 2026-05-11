from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("customers", "0001_initial"),
        ("loans", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="SMSLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("recipient", models.CharField(max_length=20)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="customers.customer")),
                ("loan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="loans.loan")),
                ("template", models.CharField(
                    choices=[
                        ("DISBURSEMENT","Loan Disbursement"),("PAYMENT_CONFIRM","Payment Confirmation"),
                        ("PAYMENT_REMINDER","Payment Reminder"),("OVERDUE_1","Overdue Day 1-7"),
                        ("OVERDUE_2","Overdue Day 8-30"),("OVERDUE_3","Overdue Day 30+"),
                        ("APPROVAL","Loan Approved"),("REJECTION","Loan Rejected"),("CUSTOM","Custom Message"),
                    ],
                    default="CUSTOM", max_length=30,
                )),
                ("message", models.TextField()),
                ("status", models.CharField(
                    choices=[("PENDING","Pending"),("SENT","Sent"),("FAILED","Failed"),("DELIVERED","Delivered")],
                    default="PENDING", max_length=12,
                )),
                ("at_message_id", models.CharField(blank=True, max_length=80)),
                ("at_cost", models.CharField(blank=True, max_length=20)),
                ("failure_reason", models.TextField(blank=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ql_sms_logs", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="EmailLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("recipient", models.EmailField()),
                ("subject", models.CharField(max_length=200)),
                ("body_text", models.TextField()),
                ("status", models.CharField(
                    choices=[("PENDING","Pending"),("SENT","Sent"),("FAILED","Failed")],
                    default="PENDING", max_length=10,
                )),
                ("error", models.TextField(blank=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ql_email_logs", "ordering": ["-created_at"]},
        ),
    ]
