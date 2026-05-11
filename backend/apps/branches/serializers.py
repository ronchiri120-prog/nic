from rest_framework import serializers
from .models import Branch, Region


class RegionSerializer(serializers.ModelSerializer):
    manager_name  = serializers.CharField(source='manager.full_name', read_only=True)
    branches_count = serializers.ReadOnlyField(source='branches.count')

    class Meta:
        model = Region
        fields = '__all__'


class BranchSerializer(serializers.ModelSerializer):
    region_name   = serializers.CharField(source='region.name', read_only=True)
    manager_name  = serializers.CharField(source='manager.full_name', read_only=True)
    staff_count   = serializers.ReadOnlyField()
    active_loans  = serializers.ReadOnlyField(source='active_loans_count')

    class Meta:
        model  = Branch
        fields = '__all__'
        read_only_fields = ['created_at']
