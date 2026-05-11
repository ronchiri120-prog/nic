from rest_framework import serializers
from .models import Account, JournalEntry, JournalLine, FiscalPeriod


class AccountSerializer(serializers.ModelSerializer):
    balance      = serializers.ReadOnlyField()
    parent_name  = serializers.CharField(source="parent.name", read_only=True, default=None)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model  = Account
        fields = ["id","code","name","account_type","parent","parent_name",
                  "description","is_active","is_control","balance","children_count"]

    def get_children_count(self, obj):
        return obj.children.count()


class JournalLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    branch_name  = serializers.CharField(source="branch.name",  read_only=True, default=None)

    class Meta:
        model  = JournalLine
        fields = ["id","account","account_code","account_name",
                  "debit_amount","credit_amount","description","branch","branch_name"]


class JournalEntrySerializer(serializers.ModelSerializer):
    lines      = JournalLineSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default=None)
    is_balanced = serializers.ReadOnlyField()

    class Meta:
        model  = JournalEntry
        fields = ["id","reference","narration","date","status","source_type",
                  "source_id","created_by_name","is_balanced","posted_at","created_at","lines"]
        read_only_fields = ["reference","posted_at","created_at"]


class JournalEntryCreateSerializer(serializers.ModelSerializer):
    """Used for creating manual journal entries with embedded lines."""
    lines = JournalLineSerializer(many=True)

    class Meta:
        model  = JournalEntry
        fields = ["narration","date","source_type","lines"]

    def create(self, validated_data):
        lines_data = validated_data.pop("lines")
        entry = JournalEntry.objects.create(**validated_data, source_type="manual")
        for ld in lines_data:
            JournalLine.objects.create(entry=entry, **ld)
        return entry


class FiscalPeriodSerializer(serializers.ModelSerializer):
    closed_by_name = serializers.CharField(source="closed_by.full_name", read_only=True, default=None)

    class Meta:
        model  = FiscalPeriod
        fields = "__all__"
        read_only_fields = ["closed_by","closed_at"]
