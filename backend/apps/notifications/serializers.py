from rest_framework import serializers
from .models import SMSLog, EmailLog


class SMSLogSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True, default="—")
    loan_ref      = serializers.CharField(source="loan.loan_id",       read_only=True, default="—")

    class Meta:
        model  = SMSLog
        fields = [
            "id", "recipient", "customer_name", "loan_ref", "template",
            "message", "status", "at_message_id", "at_cost", "sent_at", "created_at",
        ]


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EmailLog
        fields = ["id", "recipient", "subject", "status", "sent_at", "created_at"]
