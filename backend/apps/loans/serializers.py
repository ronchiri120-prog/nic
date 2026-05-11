"""loans/serializers.py"""
from rest_framework import serializers
from .models import Loan, LoanProduct, RepaymentSchedule


class LoanProductSerializer(serializers.ModelSerializer):
    verification_team_name = serializers.CharField(source='verification_team.full_name', read_only=True, default=None)
    
    class Meta:
        model  = LoanProduct
        fields = ('id','name','loan_type','min_amount','max_amount','interest_rate','tenure_days','penalty_rate','initiation_fee','first_loan_fee','repeat_loan_fee','rate_platinum','rate_gold','rate_silver','rate_arrears','is_active','verification_team','verification_team_name')


class LoanListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name',   read_only=True)
    customer_uid  = serializers.CharField(source='customer.uid',          read_only=True)
    customer_phone= serializers.CharField(source='customer.phone',        read_only=True)
    branch_name   = serializers.CharField(source='branch.name',           read_only=True)
    lo_name       = serializers.CharField(source='loan_officer.full_name',read_only=True)
    product_name  = serializers.CharField(source='product.name',          read_only=True)
    product_type  = serializers.CharField(source='product.loan_type',     read_only=True)
    outstanding   = serializers.DecimalField(source='balance', max_digits=14, decimal_places=2, read_only=True)
    credit_score  = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model  = Loan
        fields = [
            'id', 'loan_id', 'customer', 'customer_name', 'customer_uid', 'customer_phone',
            'branch_name', 'lo_name', 'product_name', 'product_type',
            'principal', 'total_amount', 'total_paid', 'balance', 'outstanding',
            'interest_rate', 'status', 'due_date', 'disbursed_at', 'created_at',
            'credit_score',
        ]


class LoanSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    product_name  = serializers.CharField(source='product.name', read_only=True)
    branch_name   = serializers.CharField(source='branch.name', read_only=True)
    schedules     = serializers.SerializerMethodField()

    class Meta:
        model  = Loan
        fields = '__all__'
        read_only_fields = ('loan_id', 'balance', 'total_paid', 'created_at', 'updated_at',
                           'verified_by', 'verified_at', 'approved_by', 'approved_at',
                           'disbursed_by', 'disbursed_at', 'branch')

    def validate(self, attrs):
        # Check for active loans in other branches for same customer (by national_id)
        customer = attrs.get('customer')
        if customer:
            from .models import Loan
            existing_loans = Loan.objects.filter(
                customer__national_id=customer.national_id,
                status__in=['ACTIVE', 'DISBURSED', 'APPROVED', 'VERIFIED']
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            # Check against customer's branch (loan will be auto-set to this)
            for existing in existing_loans:
                if existing.branch != customer.branch:
                    raise serializers.ValidationError({
                        'customer': f'Customer already has an active loan ({existing.loan_id}) '
                                   f'at branch {existing.branch.name}. '
                                   f'Cannot create loan across different branches.'
                    })
        
        return attrs

    def get_schedules(self, obj):
        return RepaymentScheduleSerializer(obj.schedules.all(), many=True).data

    def create(self, validated_data):
        loan = super().create(validated_data)
        # Auto-set branch from customer
        if not loan.branch_id and loan.customer:
            loan.branch = loan.customer.branch
            loan.save()
        return loan


class RepaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RepaymentSchedule
        fields = '__all__'
