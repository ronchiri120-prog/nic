"""customers/models.py"""
from django.db import models
from django.core.validators import RegexValidator


class Customer(models.Model):
    class Status(models.TextChoices):
        ACTIVE      = 'ACTIVE',      'Active'
        DORMANT     = 'DORMANT',     'Dormant'
        BLACKLISTED = 'BLACKLISTED', 'Blacklisted'
        DECEASED    = 'DECEASED',    'Deceased'

    class Gender(models.TextChoices):
        MALE   = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER  = 'O', 'Other'

    # Identity
    uid         = models.CharField(max_length=20, unique=True, editable=False)
    first_name  = models.CharField(max_length=80)
    last_name   = models.CharField(max_length=80)
    national_id = models.CharField(max_length=20, unique=True)
    gender      = models.CharField(max_length=1, choices=Gender.choices, default=Gender.MALE)
    dob         = models.DateField(null=True, blank=True)

    # Contact
    phone   = models.CharField(max_length=20)
    phone2  = models.CharField(max_length=20, blank=True)
    email   = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # KYC documents
    id_front  = models.ImageField(upload_to='kyc/id/', null=True, blank=True)
    id_back   = models.ImageField(upload_to='kyc/id/', null=True, blank=True)
    photo     = models.ImageField(upload_to='kyc/photos/', null=True, blank=True)

    # Location (Kenya-specific)
    county       = models.CharField(max_length=60, blank=True)
    sub_county   = models.CharField(max_length=60, blank=True)
    village      = models.CharField(max_length=80, blank=True)

    # Family / demographics
    marital_status = models.CharField(max_length=12, blank=True,
        choices=[('SINGLE','Single'),('MARRIED','Married'),('DIVORCED','Divorced'),('WIDOWED','Widowed')])
    dependants     = models.PositiveIntegerField(default=0)

    # Next of kin
    next_of_kin         = models.CharField(max_length=120, blank=True)
    next_of_kin_phone   = models.CharField(max_length=20, blank=True)
    next_of_kin_relation= models.CharField(max_length=60, blank=True)

    # Employment extras
    employer_phone   = models.CharField(max_length=20, blank=True)
    employer_address = models.TextField(blank=True)
    payslip_date     = models.DateField(null=True, blank=True)
    net_salary       = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Employment
    employer        = models.CharField(max_length=120, blank=True)
    monthly_income  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employment_type = models.CharField(max_length=40, blank=True)

    # Guarantor
    guarantor_name    = models.CharField(max_length=120, blank=True)
    guarantor_phone   = models.CharField(max_length=20, blank=True)
    guarantor_id      = models.CharField(max_length=20, blank=True)
    guarantor_relation = models.CharField(max_length=60, blank=True)



    # Business information
    business_name     = models.CharField(max_length=120, blank=True)
    business_category = models.CharField(max_length=100, blank=True)
    business_location = models.CharField(max_length=200, blank=True)
    business_address  = models.TextField(blank=True)
    home_address      = models.TextField(blank=True)

    # Geo-location
    geo_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geo_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Guarantor documents
    guarantor_id_front       = models.ImageField(upload_to='kyc/guarantor/', null=True, blank=True)
    guarantor_id_back        = models.ImageField(upload_to='kyc/guarantor/', null=True, blank=True)
    guarantor_passport       = models.ImageField(upload_to='kyc/guarantor/', null=True, blank=True)
    guarantor_address        = models.TextField(blank=True)
    guarantor_business_address = models.TextField(blank=True)

    # ── Client Tier (affects interest rate) ──────────────────────────────────
    class Tier(models.TextChoices):
        PLATINUM = 'PLATINUM', 'Platinum — 16% (≥ 5 clean loans, no arrears)'
        GOLD     = 'GOLD',     'Gold — 18% (≥ 3 clean loans)'
        SILVER   = 'SILVER',   'Silver — 20% (standard)'

    tier             = models.CharField(max_length=10, choices=Tier.choices,
                        default='SILVER',
                        help_text='Determines interest rate: Platinum=16%, Gold=18%, Silver=20%')
    tier_updated_at  = models.DateTimeField(null=True, blank=True,
                        help_text='When tier was last promoted or demoted')
    
    # ── Default Loan Product ───────────────────────────────────────────────────
    default_product  = models.ForeignKey('loans.LoanProduct', on_delete=models.SET_NULL,
                        null=True, blank=True, related_name='default_customers',
                        help_text='Default loan product for this customer')
    tier_notes       = models.TextField(blank=True,
                        help_text='Reason for tier change')
    total_loans_paid = models.IntegerField(default=0,
                        help_text='Count of fully repaid loans — used for tier calculation')
    # System
    branch          = models.ForeignKey('branches.Branch', on_delete=models.PROTECT, related_name='customers')
    loan_officer    = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='assigned_customers')
    loan_limit      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit_score    = models.IntegerField(default=0)
    status          = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    blacklist_reason = models.TextField(blank=True)
    is_active       = models.BooleanField(default=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ql_customers'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.uid})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def active_loan(self):
        return self.loans.filter(status='ACTIVE').first()

    def save(self, *args, **kwargs):
        if not self.uid:
            from django.utils.timezone import now
            count = Customer.objects.count() + 1
            self.uid = f'QL-C{str(count).zfill(4)}'
        super().save(*args, **kwargs)


class KYCDocument(models.Model):
    """KYC document record — stores S3 key + metadata, never the file itself."""
    class Status(models.TextChoices):
        PENDING  = 'PENDING',  'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    customer    = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='documents')
    category    = models.CharField(max_length=20, choices=[
        ('ID_FRONT','National ID Front'),('ID_BACK','National ID Back'),
        ('PASSPORT_PHOTO','Passport Photo'),('PAYSLIP','Payslip'),
        ('BANK_STATEMENT','Bank Statement'),('LOGBOOK','Logbook'),
        ('TITLE_DEED','Title Deed'),('GUARANTOR_ID','Guarantor ID'),('OTHER','Other'),
    ])
    s3_key      = models.CharField(max_length=400)
    filename    = models.CharField(max_length=200)
    content_type= models.CharField(max_length=50)
    file_size   = models.PositiveIntegerField(default=0, help_text='bytes')
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)
    notes       = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ql_kyc_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.customer.full_name} — {self.category}'

    def download_url(self, expiry=3600):
        from apps.customers.documents import generate_download_url
        return generate_download_url(self.s3_key, expiry)


class Lead(models.Model):
    """
    A sales lead captured by an RO or BA before customer conversion.
    BA can create, RO can create + convert, Admin/Ops can edit.
    """
    class Status(models.TextChoices):
        NEW       = 'NEW',       'New'
        CONTACTED = 'CONTACTED', 'Contacted'
        QUALIFIED = 'QUALIFIED', 'Qualified'
        CONVERTED = 'CONVERTED', 'Converted'
        LOST      = 'LOST',      'Lost'

    class Source(models.TextChoices):
        WALK_IN   = 'WALK_IN',   'Walk-in'
        REFERRAL  = 'REFERRAL',  'Referral'
        MARKETING = 'MARKETING', 'Marketing'
        SOCIAL    = 'SOCIAL',    'Social Media'
        OTHER     = 'OTHER',     'Other'

    lead_id           = models.CharField(max_length=20, unique=True, editable=False)
    first_name        = models.CharField(max_length=80)
    last_name         = models.CharField(max_length=80)
    phone             = models.CharField(max_length=20)
    national_id       = models.CharField(max_length=20, blank=True)
    gender            = models.CharField(max_length=1,
                            choices=[('M','Male'),('F','Female'),('O','Other')],
                            default='M')
    business_category = models.CharField(max_length=100, blank=True)
    business_location = models.CharField(max_length=200, blank=True)
    submarket         = models.CharField(max_length=80, blank=True,
                            help_text='Sub-market/locality within the branch area')
    notes             = models.TextField(blank=True)
    status            = models.CharField(max_length=15,
                            choices=Status.choices, default=Status.NEW)
    source            = models.CharField(max_length=40,
                            choices=Source.choices, default=Source.WALK_IN, blank=True)

    # ── Extended profile (filled during detail/convert step) ──────────────────
    phone2              = models.CharField(max_length=20, blank=True)
    marital_status      = models.CharField(max_length=12, blank=True,
                              choices=[('SINGLE','Single'),('MARRIED','Married'),
                                       ('DIVORCED','Divorced'),('WIDOWED','Widowed')])
    dob                 = models.DateField(null=True, blank=True)
    home_address        = models.TextField(blank=True)
    business_name       = models.CharField(max_length=120, blank=True)
    monthly_income      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Guarantor / NOK (collected at detail stage)
    next_of_kin         = models.CharField(max_length=120, blank=True)
    next_of_kin_phone   = models.CharField(max_length=20,  blank=True)
    next_of_kin_relation= models.CharField(max_length=60,  blank=True)
    guarantor_name      = models.CharField(max_length=120, blank=True)
    guarantor_phone     = models.CharField(max_length=20,  blank=True)
    guarantor_id        = models.CharField(max_length=20,  blank=True)
    guarantor_relation  = models.CharField(max_length=60,  blank=True)
    guarantor_address   = models.TextField(blank=True)

    # Relations
    branch      = models.ForeignKey('branches.Branch',
                    on_delete=models.PROTECT, related_name='leads')
    created_by  = models.ForeignKey('accounts.User',
                    on_delete=models.SET_NULL, null=True, related_name='leads_created')
    assigned_to = models.ForeignKey('accounts.User',
                    on_delete=models.SET_NULL, null=True, blank=True, related_name='leads_assigned')
    converted_by= models.ForeignKey('accounts.User',
                    on_delete=models.SET_NULL, null=True, blank=True, related_name='leads_converted')
    converted_at= models.DateTimeField(null=True, blank=True)
    customer    = models.OneToOneField('Customer',
                    on_delete=models.SET_NULL, null=True, blank=True, related_name='lead')

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ql_leads'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.lead_id} — {self.first_name} {self.last_name}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def save(self, *args, **kwargs):
        if not self.lead_id:
            count = Lead.objects.count() + 1
            self.lead_id = f'LD-{str(count).zfill(4)}'
        super().save(*args, **kwargs)

    def convert_to_customer(self, converted_by_user):
        """Convert this lead into a Customer record, migrating ALL captured data."""
        from django.utils import timezone
        if self.status == Lead.Status.CONVERTED and self.customer:
            return self.customer  # already converted

        # Require a real national ID for conversion
        national_id = self.national_id
        if not national_id:
            raise ValueError('National ID is required to convert a lead to a customer.')

        customer = Customer.objects.create(
            first_name            = self.first_name,
            last_name             = self.last_name,
            phone                 = self.phone,
            phone2                = getattr(self, 'phone2', '') or '',
            national_id           = national_id,
            gender                = self.gender,
            marital_status        = getattr(self, 'marital_status', '') or '',
            dob                   = getattr(self, 'dob', None),
            branch                = self.branch,
            loan_officer          = self.assigned_to or converted_by_user,
            # Business
            business_name         = getattr(self, 'business_name', '') or '',
            business_category     = self.business_category,
            business_location     = self.business_location,
            business_address      = getattr(self, 'business_location', '') or '',
            home_address          = getattr(self, 'home_address', '') or '',
            address               = getattr(self, 'home_address', '') or self.business_location or '',
            # Income / limits
            monthly_income        = getattr(self, 'monthly_income', 0) or 0,
            # Guarantor
            next_of_kin           = getattr(self, 'next_of_kin', '') or '',
            next_of_kin_phone     = getattr(self, 'next_of_kin_phone', '') or '',
            next_of_kin_relation  = getattr(self, 'next_of_kin_relation', '') or '',
            guarantor_name        = getattr(self, 'guarantor_name', '') or '',
            guarantor_phone       = getattr(self, 'guarantor_phone', '') or '',
            guarantor_id          = getattr(self, 'guarantor_id', '') or '',
            guarantor_relation    = getattr(self, 'guarantor_relation', '') or '',
            guarantor_address     = getattr(self, 'guarantor_address', '') or '',
            status                = 'ACTIVE',
        )

        self.customer     = customer
        self.status       = Lead.Status.CONVERTED
        self.converted_by = converted_by_user
        self.converted_at = timezone.now()
        self.save(update_fields=['customer','status','converted_by','converted_at'])
        return customer
