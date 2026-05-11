"""customers/serializers.py — with cross-branch duplicate prevention."""
from rest_framework import serializers
from django.conf import settings
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    tier             = serializers.CharField(read_only=True)
    tier_updated_at  = serializers.DateTimeField(read_only=True)

    full_name    = serializers.ReadOnlyField()
    branch_name  = serializers.CharField(source='branch.name',      read_only=True)
    lo_name      = serializers.CharField(source='loan_officer.full_name', read_only=True, default=None)
    region_name  = serializers.CharField(source='branch.region.name', read_only=True, default=None)
    active_loan  = serializers.SerializerMethodField()
    kyc_score    = serializers.SerializerMethodField()
    default_product_name = serializers.CharField(source='default_product.name', read_only=True, default=None)
    
    # Ensure image fields return full URLs
    id_front    = serializers.ImageField(use_url=True)
    id_back     = serializers.ImageField(use_url=True)
    photo       = serializers.ImageField(use_url=True)
    guarantor_id_front = serializers.ImageField(use_url=True)
    guarantor_id_back  = serializers.ImageField(use_url=True)
    guarantor_passport = serializers.ImageField(use_url=True)

    class Meta:
        model  = Customer
        fields = '__all__'
        read_only_fields = ['uid', 'created_at', 'updated_at', 'credit_score']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Include KYC documents from the documents table
        from .models import KYCDocument
        docs = KYCDocument.objects.filter(customer=instance)
        data['documents'] = [{
            'id': d.id,
            'category': d.category,
            'filename': d.filename,
            'status': d.status,
            'uploaded_at': d.uploaded_at.isoformat() if d.uploaded_at else None,
            'download_url': d.download_url(expiry=3600) if hasattr(d, 'download_url') else None,
        } for d in docs]
        return data

    def get_active_loan(self, obj):
        loan = obj.active_loan
        if loan:
            return {'id': loan.loan_id, 'principal': float(loan.principal),
                    'balance': float(loan.balance), 'status': loan.status,
                    'due_date': str(loan.due_date) if loan.due_date else None}
        return None

    def get_kyc_score(self, obj):
        """Returns KYC completeness 0-100."""
        checks = [
            bool(obj.national_id), bool(obj.phone), bool(obj.dob),
            bool(obj.gender), bool(obj.address), bool(obj.county),
            bool(obj.employer), bool(obj.monthly_income),
            bool(obj.next_of_kin), bool(obj.next_of_kin_phone),
            bool(obj.guarantor_name), bool(obj.guarantor_phone),
            bool(obj.id_front or obj.documents.filter(category='ID_FRONT').exists()),
            bool(obj.id_back  or obj.documents.filter(category='ID_BACK').exists()),
            bool(obj.photo    or obj.documents.filter(category='PASSPORT_PHOTO').exists()),
        ]
        return round(sum(checks) / len(checks) * 100)

    def validate_national_id(self, value):
        """Block duplicate national ID across ALL branches."""
        qs = Customer.objects.filter(national_id=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            existing = qs.first()
            raise serializers.ValidationError(
                f'National ID {value} is already registered as {existing.uid} '
                f'({existing.full_name}) at {existing.branch.name}. '
                f'A customer cannot have two profiles across branches.'
            )
        return value

    def validate_phone(self, value):
        """Block duplicate phone number across ALL branches."""
        from apps.notifications.sms import normalize_phone
        normalized = normalize_phone(value)
        if not normalized:
            raise serializers.ValidationError(
                f'Invalid phone number format. Use 07XX XXX XXX or 2547XX XXX XXX.'
            )
        # Check for existing customer with same phone (check both original and normalized)
        qs = Customer.objects.filter(phone=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            existing = qs.first()
            raise serializers.ValidationError(
                f'Phone {value} is already registered to {existing.uid} '
                f'({existing.full_name}) at {existing.branch.name}. '
                f'A customer cannot have two profiles across branches.'
            )
        # Also check normalized version
        qs2 = Customer.objects.filter(phone=normalized)
        if self.instance:
            qs2 = qs2.exclude(pk=self.instance.pk)
        if qs2.exists():
            existing = qs2.first()
            raise serializers.ValidationError(
                f'Phone {value} (normalized to {normalized}) is already registered to {existing.uid} '
                f'({existing.full_name}) at {existing.branch.name}. '
                f'A customer cannot have two profiles across branches.'
            )
        return normalized   # Store in normalized 254XXXXXXXXX format


class CustomerListSerializer(serializers.ModelSerializer):
    tier = serializers.CharField(read_only=True)

    """Compact serializer for table/list views."""
    full_name   = serializers.ReadOnlyField()
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    kyc_score   = serializers.SerializerMethodField()
    
    # Include photo and ID images for display
    photo       = serializers.ImageField(use_url=True, read_only=True)
    id_front    = serializers.ImageField(use_url=True, read_only=True)
    id_back     = serializers.ImageField(use_url=True, read_only=True)

    class Meta:
        model  = Customer
        fields = ['id','uid','full_name','national_id','phone','branch_name',
                  'loan_limit','credit_score','kyc_score','tier','status','created_at',
                  'photo','id_front','id_back']

    def get_kyc_score(self, obj):
        checks = [bool(obj.national_id),bool(obj.phone),bool(obj.dob),
                  bool(obj.gender),bool(obj.address),bool(obj.county),
                  bool(obj.employer),bool(obj.next_of_kin)]
        return round(sum(checks)/len(checks)*100)


class CustomerReferenceSerializer(serializers.ModelSerializer):
    """Minimal serializer for the reference/lookup check."""
    full_name     = serializers.ReadOnlyField()
    branch_name   = serializers.CharField(source='branch.name',      read_only=True)
    region_name   = serializers.CharField(source='branch.region.name', read_only=True, default=None)
    lo_name       = serializers.CharField(source='loan_officer.full_name', read_only=True, default=None)
    active_loans  = serializers.SerializerMethodField()
    total_exposure= serializers.SerializerMethodField()

    class Meta:
        model  = Customer
        fields = ['id','uid','full_name','national_id','phone','status',
                  'branch_name','region_name','lo_name','loan_limit',
                  'credit_score','active_loans','total_exposure','blacklist_reason']

    def get_active_loans(self, obj):
        return [{'loan_id': l.loan_id,'principal': float(l.principal),
                 'balance': float(l.balance),'status': l.status,
                 'branch': l.branch.name if l.branch else '—',
                 'due_date': str(l.due_date) if l.due_date else None}
                for l in obj.loans.filter(status__in=['ACTIVE','DEFAULT','APPROVED'])]

    def get_total_exposure(self, obj):
        from django.db.models import Sum
        return float(obj.loans.filter(status__in=['ACTIVE','DEFAULT']).aggregate(
            s=Sum('balance'))['s'] or 0)


class LeadSerializer(serializers.ModelSerializer):
    full_name         = serializers.CharField(read_only=True)
    branch_name       = serializers.CharField(source='branch.name', read_only=True)
    created_by_name   = serializers.CharField(source='created_by.full_name', read_only=True)
    assigned_to_name  = serializers.CharField(source='assigned_to.full_name', read_only=True)
    converted_by_name = serializers.CharField(source='converted_by.full_name', read_only=True)
    customer_uid      = serializers.CharField(source='customer.uid', read_only=True)
    customer_id       = serializers.IntegerField(source='customer.id', read_only=True)

    class Meta:
        from apps.customers.models import Lead
        model  = Lead
        fields = '__all__'
        read_only_fields = [
            'lead_id', 'converted_by', 'converted_at',
            'customer', 'created_at', 'updated_at',
        ]
