"""
accounts/models.py — Custom User Model with Role-Based Access
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', User.Role.SUPER_ADMIN)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        # Management
        SUPER_ADMIN      = 'SUPER_ADMIN',      'Super Admin'
        ADMIN            = 'ADMIN',            'Admin'
        RM               = 'RM',               'Regional Manager'
        BRANCH_MANAGER   = 'BRANCH_MANAGER',   'Branch Manager'
        OPERATIONS       = 'OPERATIONS',       'Operations'
        
        # IT / Tech Department
        TECH             = 'TECH',             'Tech Department'
        
        # Business Development
        BDO              = 'BDO',              'Business Development Officer'
        
        # Credit & Loans
        IDC              = 'IDC',              'IDC Credit Officer'
        LOAN_OFFICER     = 'LOAN_OFFICER',     'Loan Officer'
        FA_MANAGER       = 'FA_MANAGER',       'FA Manager'
        VERIFICATION_TEAM = 'VERIFICATION_TEAM', 'Verification Team'
        
        # Finance & Disbursement
        FINANCE          = 'FINANCE',          'Finance'
        PAYMENT_OFFICER  = 'PAYMENT_OFFICER',  'Payment Officer'
        DISBURSEMENT_OFFICER = 'DISBURSEMENT_OFFICER', 'Disbursement Officer'
        
        # Collections
        COLLECTIONS_MGR  = 'COLLECTIONS_MGR',  'Collections Manager'
        EDC_MANAGER      = 'EDC_MANAGER',      'EDC Manager'
        COLLECTIONS      = 'COLLECTIONS',      'Collections Officer'
        EXTERNAL_DEBT_COLLECTOR = 'EXTERNAL_DEBT_COLLECTOR', 'External Debt Collector'
        FIELD_AGENT      = 'FIELD_AGENT',      'Field Agent'
        
        # CRM & Marketing
        CC_MANAGER       = 'CC_MANAGER',       'CC Manager'
        CALL_CENTRE      = 'CALL_CENTRE',      'Call Centre'
        
        # Front Office
        FRONT_OFFICE     = 'FRONT_OFFICE',     'Front Office'
        
        # Read Only
        READ_ONLY        = 'READ_ONLY',        'Viewer Only'

    # Core fields
    email        = models.EmailField(unique=True)
    full_name    = models.CharField(max_length=120)
    phone        = models.CharField(max_length=20, blank=True)
    role         = models.CharField(max_length=30, choices=Role.choices, default=Role.READ_ONLY)
    branch       = models.ForeignKey(
        'branches.Branch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='staff'
    )
    region       = models.ForeignKey(
        'branches.Region', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='region_staff'
    )
    staff_id     = models.CharField(max_length=20, unique=True, blank=True)
    profile_pic  = models.ImageField(upload_to='staff/', null=True, blank=True)
    is_active    = models.BooleanField(default=True)
    # 2FA
    totp_secret      = models.CharField(max_length=64, blank=True, null=True)
    totp_enabled     = models.BooleanField(default=False)
    totp_backup_codes= models.JSONField(default=list, blank=True)
    is_staff     = models.BooleanField(default=False)

    # Targets
    disbursement_target = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Timestamps
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    last_login  = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'ql_users'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.role})'

    def save(self, *args, **kwargs):
        if not self.staff_id:
            import uuid
            self.staff_id = 'STF-' + str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """Tracks every significant action in the system."""
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action     = models.CharField(max_length=200)
    model_name = models.CharField(max_length=80)
    object_id  = models.CharField(max_length=80, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details    = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ql_audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.action} [{self.created_at}]'
