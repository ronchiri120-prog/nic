"""customers/views.py"""
import rest_framework
from rest_framework import generics, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Customer
from .serializers import CustomerSerializer, CustomerListSerializer
from apps.accounts.permissions import (
    IsLoanOfficerOrAbove, IsBranchManagerOrAbove,
    CanCreateLead, CanConvertLead, IsVerificationTeam,
)


class CustomerListCreateView(generics.ListCreateAPIView):
    filterset_fields = ['status', 'branch', 'loan_officer', 'gender']
    search_fields    = ['first_name', 'last_name', 'national_id', 'phone', 'uid']
    ordering_fields  = ['created_at', 'first_name', 'loan_limit']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CustomerListSerializer
        return CustomerSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Customer.objects.select_related('branch', 'loan_officer')
        # Verification team and super admin see all customers across all branches
        if user.role in ('VERIFICATION_TEAM', 'SUPER_ADMIN'):
            return qs
        elif user.role == 'BRANCH_MANAGER':
            qs = qs.filter(branch=user.branch)
        elif user.role in ('LOAN_OFFICER', 'BDO'):
            qs = qs.filter(loan_officer=user)
        return qs


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.select_related('branch', 'loan_officer')
    
    def get_queryset(self):
        user = self.request.user
        qs = Customer.objects.select_related('branch', 'loan_officer')
        # Verification team and super admin see all customers across all branches
        if user.role in ('VERIFICATION_TEAM', 'SUPER_ADMIN'):
            return qs
        return qs


class CustomerBlacklistView(APIView):
    def post(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            reason = request.data.get('reason', '')
            customer.status = Customer.Status.BLACKLISTED
            customer.blacklist_reason = reason
            customer.save()
            return Response({'detail': 'Customer blacklisted.'})
        except Customer.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)


class CustomerLoanHistoryView(APIView):
    def get(self, request, pk):
        from apps.loans.models import Loan
        from apps.loans.serializers import LoanListSerializer
        loans = Loan.objects.filter(customer_id=pk).order_by('-created_at')
        return Response(LoanListSerializer(loans, many=True).data)


# ─── URLs ─────────────────────────────────────────────
from django.urls import path

urlpatterns = [
    path('',                              CustomerListCreateView.as_view(),  name='customer-list'),
    path('<int:pk>/',                     CustomerDetailView.as_view(),      name='customer-detail'),
    path('<int:pk>/blacklist/',           CustomerBlacklistView.as_view(),   name='customer-blacklist'),
    path('<int:pk>/loan-history/',        CustomerLoanHistoryView.as_view(), name='customer-loans'),
]


class CustomerExportView(APIView):
    """GET /api/v1/customers/export/ — download full customer CSV"""
    permission_classes = [IsLoanOfficerOrAbove, IsVerificationTeam]
    def get(self, request):
        from apps.customers.bulk import export_customers_csv
        from apps.customers.models import Customer
        qs = Customer.objects.select_related('branch','loan_officer').all()
        # Verification team and super admin see all customers across all branches
        if request.user.role in ('VERIFICATION_TEAM', 'SUPER_ADMIN'):
            return export_customers_csv(qs)
        elif not request.user.is_superuser and hasattr(request.user, 'branch') and request.user.branch:
            qs = qs.filter(branch=request.user.branch)
        return export_customers_csv(qs)


class CustomerBulkImportView(APIView):
    """POST /api/v1/customers/bulk-import/ — upload CSV"""
    permission_classes = [IsLoanOfficerOrAbove]
    parser_classes = [rest_framework.parsers.MultiPartParser]

    def post(self, request):
        import rest_framework.parsers
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'No file uploaded. Send as multipart field "file".'}, status=400)
        if not file_obj.name.endswith('.csv'):
            return Response({'detail': 'Only .csv files are accepted.'}, status=400)
        dry_run = request.data.get('dry_run', 'false').lower() == 'true'
        from apps.customers.bulk import import_customers_csv
        result = import_customers_csv(
            file_obj,
            branch=request.user.branch,
            loan_officer=request.user,
            dry_run=dry_run,
        )
        return Response(result, status=200 if not result['errors'] else 207)


class KYCUploadURLView(APIView):
    """POST /api/v1/customers/<pk>/kyc/upload-url/ — get pre-signed S3 PUT URL"""
    permission_classes = [IsLoanOfficerOrAbove]

    def post(self, request, pk):
        from apps.customers.documents import generate_upload_url
        from apps.customers.models import KYCDocument
        try:
            customer = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response({'detail': 'Customer not found.'}, status=404)

        category     = request.data.get('category', 'OTHER')
        filename     = request.data.get('filename', 'document.pdf')
        content_type = request.data.get('content_type', 'application/pdf')

        valid_cats = [c[0] for c in KYCDocument.category.field.choices]
        if category not in valid_cats:
            return Response({'detail': f'Invalid category. Choose from: {valid_cats}'}, status=400)

        try:
            result = generate_upload_url(customer.id, category, filename, content_type)
            return Response(result)
        except ValueError as e:
            return Response({'detail': str(e)}, status=400)


class KYCDocumentListView(generics.ListAPIView):
    """GET /api/v1/customers/<pk>/kyc/ — list KYC documents with signed download URLs"""
    permission_classes = [IsLoanOfficerOrAbove]
    serializer_class   = CustomerSerializer   # We'll add a simple doc serializer

    def list(self, request, pk=None):
        from apps.customers.models import KYCDocument
        docs = KYCDocument.objects.filter(customer_id=pk).select_related('reviewed_by')
        data = [{
            'id':          d.id,
            'category':    d.category,
            'filename':    d.filename,
            'status':      d.status,
            'uploaded_at': d.uploaded_at.isoformat(),
            'download_url':d.download_url(expiry=3600),
            'reviewed_by': d.reviewed_by.full_name if d.reviewed_by else None,
            'notes':       d.notes,
        } for d in docs]
        return Response(data)


class KYCDocumentConfirmView(APIView):
    """
    POST /api/v1/customers/<pk>/kyc/confirm/
    Called after a successful S3 upload — creates the KYCDocument record.
    """
    permission_classes = [IsLoanOfficerOrAbove]

    def post(self, request, pk):
        from apps.customers.models import KYCDocument
        try:
            customer = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response({'detail': 'Customer not found.'}, status=404)

        s3_key       = request.data.get('s3_key')
        category     = request.data.get('category', 'OTHER')
        filename     = request.data.get('filename', 'document')
        content_type = request.data.get('content_type', 'application/pdf')
        file_size    = request.data.get('file_size', 0)

        if not s3_key:
            return Response({'detail': 's3_key is required.'}, status=400)

        doc = KYCDocument.objects.create(
            customer=customer, category=category, s3_key=s3_key,
            filename=filename, content_type=content_type, file_size=file_size,
        )
        return Response({
            'id':       doc.id,
            'category': doc.category,
            'status':   doc.status,
        }, status=201)


class CustomerReferenceView(APIView):
    """
    GET /api/v1/customers/reference/?q=<national_id or phone>
    Cross-branch customer lookup — used before registering a new customer
    to prevent duplicate profiles and detect existing exposure.
    Returns all matching customers regardless of branch.
    """
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request):
        from apps.customers.serializers import CustomerReferenceSerializer
        from apps.notifications.sms import normalize_phone

        q = request.query_params.get("q", "").strip()
        if not q or len(q) < 4:
            return Response(
                {"detail": "Provide at least 4 characters — national ID or phone number."},
                status=400,
            )

        # Normalize phone if looks like a phone number
        normalized_phone = normalize_phone(q)

        from django.db.models import Q
        qs = Customer.objects.filter(
            Q(national_id__iexact=q) |
            Q(phone=q) |
            Q(phone=normalized_phone) if normalized_phone else Q(national_id__iexact=q) | Q(phone=q)
        ).select_related("branch__region", "loan_officer")

        if not qs.exists():
            return Response({
                "found": False,
                "count": 0,
                "customers": [],
                "message": f"No customer found with ID or phone matching '{q}'.",
            })

        data = CustomerReferenceSerializer(qs, many=True).data
        flags = []
        if len(data) > 1:
            flags.append(f"WARNING: {len(data)} profiles found — possible duplicates across branches.")
        for c in data:
            if c["status"] == "BLACKLISTED":
                flags.append(f"BLACKLISTED: {c['uid']} ({c['full_name']}) — {c.get('blacklist_reason','reason not recorded')}")
            if c["active_loans"]:
                branches = [l["branch"] for l in c["active_loans"]]
                flags.append(f"ACTIVE EXPOSURE: {c['uid']} has active loans at: {', '.join(branches)}")

        return Response({
            "found":     True,
            "count":     len(data),
            "customers": data,
            "flags":     flags,
        })


class CustomerTierView(APIView):
    """
    GET  /api/v1/customers/<pk>/tier/   — get tier info + history
    POST /api/v1/customers/<pk>/tier/   — manually override tier (Admin/HOP/GM only)
    """
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request, pk):
        from apps.loans.pricing import get_customer_tier, get_effective_rate, get_processing_fee
        from apps.loans.models import Loan
        try:
            customer = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response({'detail': 'Customer not found.'}, status=404)

        computed_tier = get_customer_tier(customer)
        clean_loans   = Loan.objects.filter(customer=customer, status='CLOSED').count()
        active_loans  = Loan.objects.filter(customer=customer, status='ACTIVE').count()
        total_loans   = Loan.objects.filter(customer=customer).count()

        from apps.loans.pricing import RATE_PLATINUM, RATE_GOLD, RATE_SILVER, FEE_FIRST_LOAN, FEE_REPEAT_LOAN
        fee, is_first = get_processing_fee(customer)

        return Response({
            'uid':            customer.uid,
            'name':           customer.full_name,
            'current_tier':   customer.tier,
            'computed_tier':  computed_tier,
            'tier_in_sync':   customer.tier == computed_tier,
            'tier_updated_at':str(customer.tier_updated_at) if customer.tier_updated_at else None,
            'tier_notes':     customer.tier_notes,
            'loan_history': {
                'total_loans':    total_loans,
                'closed_loans':   clean_loans,
                'active_loans':   active_loans,
            },
            'pricing': {
                'rate_platinum': float(RATE_PLATINUM),
                'rate_gold':     float(RATE_GOLD),
                'rate_silver':   float(RATE_SILVER),
                'current_rate':  float({'PLATINUM': RATE_PLATINUM, 'GOLD': RATE_GOLD}.get(customer.tier, RATE_SILVER)),
                'processing_fee': float(fee),
                'is_first_loan':  is_first,
            },
            'tier_criteria': {
                'platinum': 'Minimum 5 fully repaid loans, zero arrears in 12 months',
                'gold':     'Minimum 3 fully repaid loans, at most 1 arrears incident in 12 months',
                'silver':   'Standard / new customers',
                'demotion': 'Any write-off OR 3+ arrears incidents in 12 months → Silver',
            },
        })

    def post(self, request, pk):
        """Manual tier override by Admin, HOP, or GM."""
        from apps.accounts.models import User
        allowed_roles = {User.Role.SUPER_ADMIN, User.Role.HOP, User.Role.GM}
        if request.user.role not in allowed_roles and not request.user.is_superuser:
            return Response({'detail': 'Only Admin, HOP, or GM can override customer tiers.'}, status=403)

        try:
            customer = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response({'detail': 'Customer not found.'}, status=404)

        new_tier = request.data.get('tier', '').upper()
        if new_tier not in ('PLATINUM', 'GOLD', 'SILVER'):
            return Response({'detail': 'tier must be PLATINUM, GOLD, or SILVER.'}, status=400)

        old_tier = customer.tier
        notes    = request.data.get('notes', '')
        from django.utils import timezone as tz
        customer.tier            = new_tier
        customer.tier_updated_at = tz.now()
        customer.tier_notes      = (
            f'Manual override by {request.user.full_name} ({request.user.role}) '
            f'on {tz.now().strftime("%d %b %Y")}: {old_tier} → {new_tier}. '
            f'Reason: {notes or "not stated"}'
        )
        customer.save(update_fields=['tier', 'tier_updated_at', 'tier_notes'])

        # Audit log
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=request.user, action=f'Manual tier override: {old_tier} → {new_tier}',
            model_name='Customer', object_id=str(customer.id),
            details={'old_tier': old_tier, 'new_tier': new_tier, 'notes': notes},
        )

        return Response({
            'detail':   f'{customer.full_name} tier changed: {old_tier} → {new_tier}.',
            'uid':      customer.uid,
            'old_tier': old_tier,
            'new_tier': new_tier,
        })


# ─── LEAD VIEWS ───────────────────────────────────────────────────────────────
from .models import Lead
from .serializers import LeadSerializer


class LeadListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/customers/leads/        — list leads (RO/BA sees own branch, Admin sees all)
    POST /api/v1/customers/leads/        — create lead (BA, RO, Marketing, BDM, or above)
    """
    serializer_class  = LeadSerializer
    permission_classes = [CanCreateLead]
    search_fields     = ['first_name','last_name','phone','national_id','lead_id']
    filterset_fields  = ['status','source','branch','created_by','assigned_to']
    ordering_fields   = ['created_at','status']

    def get_queryset(self):
        user = self.request.user
        qs   = Lead.objects.select_related('branch','created_by','assigned_to','converted_by','customer')
        
        # Role-based filtering
        branch_level_roles = ['BDO', 'IDC', 'LOAN_OFFICER']
        regional_level_roles = ['BRANCH_MANAGER', 'RM']
        
        if user.role in branch_level_roles and user.branch_id:
            qs = qs.filter(branch=user.branch)
        elif user.role in regional_level_roles and user.region:
            qs = qs.filter(branch__region=user.region)
        
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        # Auto-assign branch from logged-in user if not provided
        branch = serializer.validated_data.get('branch') or user.branch
        serializer.save(
            created_by  = user,
            assigned_to = user if user.role in ('BDO','LOAN_OFFICER') else None,
            branch      = branch,
        )


class LeadDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/customers/leads/<pk>/  — get lead
    PATCH /api/v1/customers/leads/<pk>/  — edit lead (RO, Admin, Ops)
    """
    serializer_class = LeadSerializer
    queryset         = Lead.objects.select_related('branch','created_by','assigned_to','customer')

    def get_permissions(self):
        # BA can only create (POST), not edit
        if self.request.method in ('PUT','PATCH'):
            return [IsLoanOfficerOrAbove()]
        return super().get_permissions()


class LeadConvertView(APIView):
    """
    POST /api/v1/customers/leads/<pk>/convert/
    Converts lead → customer. RO and above only — BA cannot convert.
    """
    permission_classes = [CanConvertLead]

    def post(self, request, pk):
        try:
            lead = Lead.objects.get(pk=pk)
        except Lead.DoesNotExist:
            return Response({'detail': 'Lead not found.'}, status=404)

        if lead.status == 'CONVERTED':
            return Response({
                'detail':       'Lead already converted.',
                'customer_uid': lead.customer.uid if lead.customer else None,
                'customer_id':  lead.customer.id  if lead.customer else None,
            }, status=400)

        try:
            customer = lead.convert_to_customer(converted_by_user=request.user)
            # Audit
            from apps.accounts.models import AuditLog
            AuditLog.objects.create(
                user=request.user, action='Lead Converted',
                model_name='Lead', object_id=str(lead.id),
                details={'lead_id': lead.lead_id, 'customer_uid': customer.uid},
            )
            return Response({
                'detail':       f'{lead.full_name} converted to customer.',
                'customer_uid': customer.uid,
                'customer_id':  customer.id,
            }, status=201)
        except Exception as e:
            return Response({'detail': str(e)}, status=400)
