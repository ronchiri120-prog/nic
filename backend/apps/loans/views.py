"""loans/views.py"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import Loan, LoanProduct
from .serializers import LoanSerializer, LoanListSerializer, LoanProductSerializer
from apps.accounts.permissions import (
    IsLoanOfficerOrAbove, IsBranchManagerOrAbove,
    IsVerificationTeam, CanApproveLoan
)


class LoanProductListCreateView(generics.ListCreateAPIView):
    queryset = LoanProduct.objects.filter(is_active=True)
    serializer_class = LoanProductSerializer


class LoanProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LoanProduct.objects.all()
    serializer_class = LoanProductSerializer


class LoanListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsLoanOfficerOrAbove]
    filterset_fields = ['status', 'branch', 'product', 'loan_officer']
    search_fields    = ['loan_id', 'customer__first_name', 'customer__last_name', 'customer__national_id']
    ordering_fields  = ['created_at', 'principal', 'due_date']

    def get_serializer_class(self):
        return LoanListSerializer if self.request.method == 'GET' else LoanSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Loan.objects.select_related('customer', 'branch', 'loan_officer', 'product')
        if user.role == 'BRANCH_MANAGER':
            qs = qs.filter(branch=user.branch)
        elif user.role in ('LOAN_OFFICER', 'BDO', 'IDC'):
            qs = qs.filter(loan_officer=user)
        # VERIFICATION_TEAM sees all loans across all branches
        elif user.role == 'VERIFICATION_TEAM':
            pass
        return qs

    def perform_create(self, serializer):
        customer = serializer.validated_data.get('customer')
        # Check if customer has any active loans
        active_statuses = [Loan.Status.PENDING, Loan.Status.VERIFIED, Loan.Status.APPROVED, Loan.Status.ACTIVE, Loan.Status.DEFAULT]
        if customer and Loan.objects.filter(customer=customer, status__in=active_statuses).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'customer': 'Customer has an active loan. Cannot create a new loan until the existing loan is cleared.'})
        
        # Also check if customer has active loans with same phone number or national ID (prevent duplicate customers)
        if customer:
            from apps.customers.models import Customer
            # Check by phone number
            customers_with_same_phone = Customer.objects.filter(phone=customer.phone).exclude(id=customer.id)
            if customers_with_same_phone.exists():
                for cust in customers_with_same_phone:
                    if Loan.objects.filter(customer=cust, status__in=active_statuses).exists():
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'customer': 'Customer with this phone number has an active loan. Cannot create a new loan until the existing loan is cleared.'})
            # Check by national ID
            customers_with_same_id = Customer.objects.filter(national_id=customer.national_id).exclude(id=customer.id)
            if customers_with_same_id.exists():
                for cust in customers_with_same_id:
                    if Loan.objects.filter(customer=cust, status__in=active_statuses).exists():
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'customer': 'Customer with this national ID has an active loan. Cannot create a new loan until the existing loan is cleared.'})
        
        loan = serializer.save(
            loan_officer=self.request.user,
            branch=self.request.user.branch,
        )


class LoanDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsLoanOfficerOrAbove]
    serializer_class = LoanSerializer
    queryset = Loan.objects.select_related('customer', 'branch', 'loan_officer', 'product')
    
    def get_queryset(self):
        user = self.request.user
        qs = Loan.objects.select_related('customer', 'branch', 'loan_officer', 'product')
        # VERIFICATION_TEAM sees all loans across all branches
        if user.role == 'VERIFICATION_TEAM':
            return qs
        elif user.role == 'BRANCH_MANAGER':
            qs = qs.filter(branch=user.branch)
        elif user.role in ('LOAN_OFFICER', 'BDO', 'IDC'):
            qs = qs.filter(loan_officer=user)
        return qs


class LoanVerifyView(APIView):
    """Verification team verifies loan documents before approval."""
    permission_classes = [IsVerificationTeam]

    def post(self, request, pk):
        try:
            loan = Loan.objects.get(pk=pk, status=Loan.Status.PENDING)
            notes = request.data.get('notes', '')
            
            # Check if the product has an assigned verification team member
            if loan.product and loan.product.verification_team:
                # Only the assigned verification team member can verify
                if request.user != loan.product.verification_team:
                    return Response({
                        'detail': f'This loan product is assigned to {loan.product.verification_team.full_name} for verification.'
                    }, status=403)
            
            loan.status = Loan.Status.VERIFIED
            loan.verified_by = request.user
            loan.verified_at = timezone.now()
            loan.verification_notes = notes
            loan.save()
            return Response({'detail': f'Loan {loan.loan_id} verified.', 'loan_id': loan.loan_id})
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found or not pending.'}, status=404)


class LoanApproveView(APIView):
    permission_classes = [CanApproveLoan]

    def post(self, request, pk):
        try:
            loan = Loan.objects.get(pk=pk, status=Loan.Status.VERIFIED)
            loan.status = Loan.Status.APPROVED
            loan.approved_by = request.user
            loan.approved_at = timezone.now()
            loan.save()
            # Fire async notifications
            try:
                from apps.notifications.tasks import task_sms_loan_approved, task_email_loan_approved
                task_sms_loan_approved.delay(loan.id)
                task_email_loan_approved.delay(loan.id)
            except Exception:
                pass  # Never block approval on notification failure
            return Response({'detail': f'Loan {loan.loan_id} approved.', 'loan_id': loan.loan_id})
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found or not in VERIFIED status. Loans must be verified by the Verification Team before approval.'}, status=404)


class LoanRejectView(APIView):
    permission_classes = [CanApproveLoan]

    def post(self, request, pk):
        try:
            loan = Loan.objects.get(pk=pk, status=Loan.Status.PENDING)
            loan.status = Loan.Status.REJECTED
            reason = request.data.get('reason', '')
            loan.rejection_reason = reason
            loan.save()
            try:
                from apps.notifications.tasks import task_sms_loan_rejected, task_email_loan_rejected
                task_sms_loan_rejected.delay(loan.id)
                task_email_loan_rejected.delay(loan.id, reason)
            except Exception:
                pass
            return Response({'detail': f'Loan {loan.loan_id} rejected.'})
        except Loan.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)


class LoanDisburseView(APIView):
    """Disburse an approved loan via M-Pesa or other method. BM, BDM, or HOP can disburse."""
    permission_classes = [IsLoanOfficerOrAbove]

    def post(self, request, pk):
        from apps.payments.mpesa import initiate_b2c
        # Only BM, RM, Operations, or above can disburse
        allowed_roles = ['BRANCH_MANAGER', 'RM', 'OPERATIONS', 'BDO', 'SUPER_ADMIN']
        if request.user.role not in allowed_roles:
            return Response({'detail': 'Only Branch Manager, Regional Manager, Operations, or BDO can disburse loans.'}, status=403)
        
        try:
            loan = Loan.objects.get(pk=pk, status=Loan.Status.APPROVED)
            method = request.data.get('method', 'MPESA')
            loan.status = Loan.Status.ACTIVE
            loan.disbursement_method = method
            loan.disbursed_by = request.user
            loan.disbursed_at = timezone.now()
            loan.due_date = (timezone.now() + timedelta(days=loan.tenure_days)).date()
            loan.save()
            # Fire disbursement notifications
            try:
                from apps.notifications.tasks import task_sms_loan_disbursed, task_email_loan_disbursed
                task_sms_loan_disbursed.delay(loan.id)
                task_email_loan_disbursed.delay(loan.id)
            except Exception:
                pass

            # Trigger M-Pesa B2C if applicable
            if method == 'MPESA':
                phone = loan.customer.phone
                try:
                    result = initiate_b2c(phone, float(loan.principal), loan.loan_id)
                    loan.mpesa_conversation_id = result.get('ConversationID', '')
                    loan.save(update_fields=['mpesa_conversation_id'])
                except Exception as e:
                    pass  # Log and continue — disburse status saved regardless

            # Post disbursement to General Ledger
            try:
                from apps.accounting.gl_service import post_loan_disbursement, post_initiation_fee
                post_loan_disbursement(loan, user=request.user)
                if loan.processing_fee and float(loan.processing_fee) > 0:
                    post_initiation_fee(loan, user=request.user)
            except Exception:
                pass  # GL failure must not block disbursement

            return Response({'detail': f'Loan {loan.loan_id} disbursed.', 'due_date': str(loan.due_date)})
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found or not approved.'}, status=404)


class LoanMarkDefaultView(APIView):
    permission_classes = [CanApproveLoan]

    def post(self, request, pk):
        try:
            loan = Loan.objects.get(pk=pk, status=Loan.Status.ACTIVE)
            loan.status = Loan.Status.DEFAULT
            loan.save()
            return Response({'detail': 'Loan marked as default.'})
        except Loan.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)


class CreditScoreView(APIView):
    """Run credit score for a customer + loan amount combination."""
    permission_classes = [IsLoanOfficerOrAbove]

    def post(self, request):
        from apps.customers.models import Customer
        from apps.loans.credit_scoring import score_loan_application
        from decimal import Decimal

        customer_id = request.data.get('customer_id')
        loan_amount = request.data.get('loan_amount')
        product_id  = request.data.get('product_id')

        if not customer_id or not loan_amount:
            return Response({'detail': 'customer_id and loan_amount required.'}, status=400)

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'detail': 'Customer not found.'}, status=404)

        product = None
        if product_id:
            try:
                product = LoanProduct.objects.get(pk=product_id)
            except LoanProduct.DoesNotExist:
                pass

        result = score_loan_application(customer, Decimal(str(loan_amount)), product=product)

        # Persist score to customer record
        customer.credit_score = result.score
        customer.save(update_fields=['credit_score'])

        return Response({
            'customer_id':    result.customer_id,
            'customer_name':  customer.full_name,
            'loan_amount':    float(result.loan_amount),
            'score':          result.score,
            'risk_grade':     result.risk_grade,
            'recommendation': result.recommendation,
            'approved':       result.approved,
            'risk_color':     result.risk_color,
            'flags':          result.flags,
            'breakdown': [
                {
                    'factor':    b.factor,
                    'max_score': b.max_score,
                    'score':     b.score,
                    'reason':    b.reason,
                    'pct':       round(b.score / b.max_score * 100, 1),
                }
                for b in result.breakdown
            ],
        })


class LoanRestructureView(APIView):
    """Unified loan restructuring endpoint."""
    permission_classes = [CanApproveLoan]

    def post(self, request, pk):
        from apps.loans.restructuring import extend_tenure, reduce_interest_rate, topup_loan, partial_write_off
        from decimal import Decimal

        try:
            loan = Loan.objects.select_related('customer','branch','product').get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=404)

        action = request.data.get('action')
        reason = request.data.get('reason', '')

        try:
            if action == 'EXTEND_TENURE':
                result = extend_tenure(loan, int(request.data['new_tenure_days']), user=request.user, reason=reason)
            elif action == 'REDUCE_RATE':
                result = reduce_interest_rate(loan, Decimal(str(request.data['new_rate'])), user=request.user, reason=reason)
            elif action == 'TOP_UP':
                result = topup_loan(loan, Decimal(str(request.data['topup_amount'])), user=request.user, reason=reason)
            elif action == 'WRITE_OFF':
                result = partial_write_off(loan, Decimal(str(request.data['writeoff_amount'])), user=request.user, reason=reason)
            else:
                return Response({'detail': 'action must be one of: EXTEND_TENURE, REDUCE_RATE, TOP_UP, WRITE_OFF'}, status=400)
            return Response(result)
        except ValueError as e:
            return Response({'detail': str(e)}, status=400)


class LoanExportView(APIView):
    """GET /api/v1/loans/export/ — download full loan portfolio CSV"""
    permission_classes = [IsLoanOfficerOrAbove]
    def get(self, request):
        from apps.customers.bulk import export_loans_csv
        qs = Loan.objects.select_related('customer','product','branch','loan_officer').all()
        if not request.user.is_superuser and hasattr(request.user,'branch') and request.user.branch:
            qs = qs.filter(branch=request.user.branch)
        return export_loans_csv(qs)


# ── Tier pricing hook (called from perform_create if overridden) ──────────────
def _apply_tier_pricing(customer, product, principal):
    from apps.loans.pricing import price_new_loan
    from decimal import Decimal
    try:
        return price_new_loan(customer, Decimal(str(principal)), product)
    except Exception:
        return {}
