"""accounts/serializers.py"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, AuditLog


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extends JWT payload with user role and branch info."""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['full_name'] = user.full_name
        token['role']      = user.role
        token['email']     = user.email
        token['staff_id']  = user.staff_id
        token['branch_id'] = user.branch_id
        token['region_id'] = user.region_id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id':        self.user.id,
            'full_name': self.user.full_name,
            'email':     self.user.email,
            'role':      self.user.role,
            'staff_id':  self.user.staff_id,
            'branch':    self.user.branch.name if self.user.branch else None,
            'branch_id': self.user.branch_id,
            'region':    self.user.region.name if self.user.region else None,
            'region_id': self.user.region_id,
        }
        return data


class UserSerializer(serializers.ModelSerializer):
    totp_enabled = serializers.BooleanField(read_only=True)

    branch_name = serializers.CharField(source='branch.name', read_only=True)
    branch_type = serializers.CharField(source='branch.branch_type', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)
    password    = serializers.CharField(write_only=True, required=False)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'role', 'staff_id',
            'branch', 'branch_name', 'branch_type', 'region', 'region_name',
            'disbursement_target', 'is_active', 'last_login', 'created_at', 'password', 'totp_enabled',
        ]
        read_only_fields = ['staff_id', 'last_login', 'created_at', 'totp_enabled']

    def validate(self, attrs):
        # Ensure HQ roles are only assigned to HQ branches
        role = attrs.get('role')
        branch = attrs.get('branch')
        
        HQ_ROLES = ['RM', 'OPERATIONS']
        
        if role in HQ_ROLES and branch:
            if branch.branch_type != 'HQ':
                raise serializers.ValidationError({
                    'branch': f'{role} role can only be assigned to Headquarters (HQ) branches.'
                })
        
        return attrs

    def create(self, validated_data):
        pw = validated_data.pop('password', None)
        user = User(**validated_data)
        if pw:
            user.set_password(pw)
        user.save()
        return user

    def update(self, instance, validated_data):
        pw = validated_data.pop('password', None)
        if pw:
            instance.set_password(pw)
        return super().update(instance, validated_data)


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model  = AuditLog
        fields = ['id', 'user_name', 'action', 'model_name', 'object_id', 'details', 'created_at']
