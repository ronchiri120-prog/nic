from rest_framework import serializers
from .models import Asset

class AssetSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    loan_id       = serializers.CharField(source="loan.loan_id", read_only=True)
    ltv           = serializers.ReadOnlyField()

    class Meta:
        model  = Asset
        fields = "__all__"
        read_only_fields = ["asset_id", "created_at"]
