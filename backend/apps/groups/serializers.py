from rest_framework import serializers
from .models import LoanGroup, GroupMembership, GroupLoan, GroupLoanShare


class GroupMembershipSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    class Meta:
        model  = GroupMembership
        fields = ["id","customer","customer_name","role","joined_at","is_active","shares"]


class LoanGroupSerializer(serializers.ModelSerializer):
    member_count       = serializers.ReadOnlyField()
    active_loans_count = serializers.ReadOnlyField()
    branch_name        = serializers.CharField(source="branch.name", read_only=True)
    lo_name            = serializers.CharField(source="loan_officer.full_name", read_only=True, default=None)
    chairperson_name   = serializers.CharField(source="chairperson.full_name", read_only=True, default=None)
    memberships        = GroupMembershipSerializer(many=True, read_only=True)

    class Meta:
        model  = LoanGroup
        fields = ["id","group_id","name","branch","branch_name","loan_officer","lo_name",
                  "chairperson","chairperson_name","status","meeting_day","meeting_location",
                  "max_members","group_fund","member_count","active_loans_count","memberships","created_at"]
        read_only_fields = ["group_id","created_at"]


class GroupLoanShareSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.customer.full_name", read_only=True)
    class Meta:
        model  = GroupLoanShare
        fields = ["id","member","member_name","amount","total_due","total_paid","balance"]


class GroupLoanSerializer(serializers.ModelSerializer):
    group_name  = serializers.CharField(source="group.name", read_only=True)
    shares      = GroupLoanShareSerializer(many=True, read_only=True)
    class Meta:
        model  = GroupLoan
        fields = ["id","group_loan_id","group","group_name","product","total_amount",
                  "interest_rate","tenure_days","status","approved_at","disbursed_at",
                  "due_date","shares","created_at"]
        read_only_fields = ["group_loan_id","created_at"]
