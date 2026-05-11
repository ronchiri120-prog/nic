"""CRM serializers for customer interactions"""
from rest_framework import serializers
from .models import CRMInteraction


class CRMInteractionSerializer(serializers.ModelSerializer):
    """Serializer for CRM interactions"""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    customer_branch = serializers.CharField(source='customer.branch.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)
    loan_id = serializers.CharField(source='loan.loan_id', read_only=True, allow_null=True)
    
    class Meta:
        model = CRMInteraction
        fields = [
            'id',
            'customer',
            'customer_name',
            'customer_phone',
            'customer_branch',
            'conversation_method',
            'conversation_purpose',
            'reason_for_default',
            'outcome',
            'outcome_details',
            'recording_file',
            'recording_transcript',
            'next_interaction_date',
            'next_step',
            'ptp_amount',
            'ptp_date',
            'recorded_by',
            'recorded_by_name',
            'created_at',
            'updated_at',
            'loan',
            'loan_id',
        ]
        read_only_fields = ['recorded_by', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Set recorded_by to current user on creation"""
        validated_data['recorded_by'] = self.context['request'].user
        # Set customer_name and customer_phone from customer
        customer = validated_data.get('customer')
        if customer:
            validated_data['customer_name'] = customer.full_name
            validated_data['customer_phone'] = customer.phone
        return super().create(validated_data)


class CRMInteractionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    customer_branch = serializers.CharField(source='customer.branch.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)
    loan_id = serializers.CharField(source='loan.loan_id', read_only=True, allow_null=True)
    
    class Meta:
        model = CRMInteraction
        fields = [
            'id',
            'customer',
            'customer_name',
            'customer_phone',
            'customer_branch',
            'conversation_method',
            'conversation_purpose',
            'outcome',
            'next_interaction_date',
            'ptp_amount',
            'ptp_date',
            'recorded_by_name',
            'created_at',
            'loan_id',
        ]
