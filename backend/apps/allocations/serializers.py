from rest_framework import serializers
from .models import Allocation

class AllocationSerializer(serializers.ModelSerializer):
    agent_name  = serializers.CharField(source="agent.full_name", read_only=True)
    loan_id     = serializers.CharField(source="loan.loan_id", read_only=True)
    customer    = serializers.CharField(source="loan.customer.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model  = Allocation
        fields = "__all__"
