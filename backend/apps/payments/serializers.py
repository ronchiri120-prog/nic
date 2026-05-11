"""payments/serializers.py"""
from rest_framework import serializers
from .models import Payment, MpesaTransaction


class PaymentSerializer(serializers.ModelSerializer):
    loan_id       = serializers.CharField(source='loan.loan_id', read_only=True)
    customer_name = serializers.CharField(source='loan.customer.full_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)

    class Meta:
        model  = Payment
        fields = '__all__'
        read_only_fields = ['ref', 'created_at']


class MpesaTransactionSerializer(serializers.ModelSerializer):
    loan_id = serializers.CharField(source='loan.loan_id', read_only=True)

    class Meta:
        model  = MpesaTransaction
        fields = '__all__'
