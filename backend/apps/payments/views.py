"""payments/views.py"""
import rest_framework.parsers
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from .models import Payment, MpesaTransaction
from .serializers import PaymentSerializer, MpesaTransactionSerializer
from .mpesa import initiate_stk_push
from apps.accounts.models import User
from apps.accounts.permissions import CanUploadPayment


class PaymentListCreateView(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    filterset_fields = ['method', 'payment_type', 'loan']
    search_fields    = ['ref', 'mpesa_ref', 'loan__loan_id', 'loan__customer__first_name']
    ordering_fields  = ['paid_at', 'amount']

    def get_queryset(self):
        return Payment.objects.select_related('loan__customer', 'recorded_by').all()

    def perform_create(self, serializer):
        payment = serializer.save(recorded_by=self.request.user, paid_at=timezone.now())
        # Auto-post to GL
        try:
            from apps.accounting.gl_service import post_payment_received
            post_payment_received(payment, user=self.request.user)
        except Exception as gl_err:
            import logging
            logging.getLogger("apps").warning(f"GL post failed for payment {payment.ref}: {gl_err}")
        # Recalculate customer tier if loan just closed
        try:
            payment.loan.refresh_from_db()
            if payment.loan.status == 'CLOSED':
                from apps.loans.pricing import recalculate_and_save_tier
                recalculate_and_save_tier(payment.loan.customer, user=payment.recorded_by)
        except Exception:
            pass

        # Fire async notifications
        try:
            from apps.notifications.tasks import task_sms_payment_confirmed, task_email_payment_received
            task_sms_payment_confirmed.delay(payment.id)
            task_email_payment_received.delay(payment.id)
        except Exception:
            pass


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.select_related('loan__customer', 'recorded_by')


class MpesaSTKPushView(APIView):
    """Trigger STK Push to customer phone for collection."""
    def post(self, request):
        phone  = request.data.get('phone')
        amount = request.data.get('amount')
        loan_id = request.data.get('loan_id')
        if not all([phone, amount, loan_id]):
            return Response({'detail': 'phone, amount and loan_id required.'}, status=400)
        try:
            result = initiate_stk_push(phone, float(amount), loan_id)
            return Response(result)
        except Exception as e:
            return Response({'detail': str(e)}, status=500)


class MpesaCallbackView(APIView):
    """Receives M-Pesa payment callback and records payment."""
    permission_classes = []  # Public endpoint for Safaricom

    def post(self, request, txn_type):
        data = request.data
        if txn_type == 'stk':
            self._handle_stk(data)
        elif txn_type == 'b2c':
            self._handle_b2c(data)
        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

    def _handle_stk(self, data):
        from apps.loans.models import Loan
        try:
            body = data.get('Body', {}).get('stkCallback', {})
            if body.get('ResultCode') != 0:
                return
            items = {i['Name']: i.get('Value') for i in body.get('CallbackMetadata', {}).get('Item', [])}
            receipt   = items.get('MpesaReceiptNumber', '')
            amount    = items.get('Amount', 0)
            phone     = str(items.get('PhoneNumber', ''))
            loan_id   = body.get('AccountReference', '')
            loan = Loan.objects.filter(loan_id=loan_id).first()
            if loan:
                payment = Payment.objects.create(
                    loan=loan, amount=amount, method='MPESA',
                    payment_type='PARTIAL', mpesa_ref=receipt, phone=phone,
                    paid_at=timezone.now(),
                )
                try:
                    from apps.notifications.tasks import task_sms_payment_confirmed, task_email_payment_received
                    task_sms_payment_confirmed.delay(payment.id)
                    task_email_payment_received.delay(payment.id)
                except Exception:
                    pass
        except Exception as e:
            import logging
            logging.getLogger('apps').error(f'STK Callback error: {e}')

    def _handle_b2c(self, data):
        """Handle B2C result callback — update transaction status and loan disburse code."""
        try:
            result = data.get('Result', {})
            result_code = result.get('ResultCode', -1)
            conversation_id = result.get('ConversationID', '')
            transaction_id  = result.get('TransactionID', '')

            # Update MpesaTransaction
            txn = MpesaTransaction.objects.filter(conversation_id=conversation_id).first()
            if txn:
                txn.status         = 'SUCCESS' if result_code == 0 else 'FAILED'
                txn.mpesa_receipt  = transaction_id
                txn.result_desc    = result.get('ResultDesc', '')
                from django.utils import timezone
                txn.completed_at   = timezone.now()
                txn.save(update_fields=['status','mpesa_receipt','result_desc','completed_at'])

                # Update loan with M-Pesa disburse code
                if result_code == 0 and txn.loan:
                    txn.loan.mpesa_disburse_code = transaction_id
                    txn.loan.status = 'ACTIVE'
                    txn.loan.save(update_fields=['mpesa_disburse_code', 'status'])
        except Exception as e:
            import logging
            logging.getLogger('apps').error(f'B2C callback error: {e}')


class MpesaTransactionListView(generics.ListAPIView):
    serializer_class = MpesaTransactionSerializer
    queryset = MpesaTransaction.objects.select_related('loan').all()
    filterset_fields = ['txn_type', 'status']


class MpesaC2BCallbackView(APIView):
    """
    POST /api/v1/payments/mpesa/c2b/
    Receives Safaricom C2B (PayBill) real-time notifications.
    Customers pay via PayBill → account number = Loan ID.
    Daraja calls this URL automatically on every payment.
    """
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        import logging
        logger = logging.getLogger('apps.payments')

        data = request.data
        logger.info(f'C2B callback: {data}')

        # Safaricom sends different payload formats (v1 vs v2)
        trans_type    = data.get('TransactionType', '')
        amount        = float(data.get('TransAmt') or data.get('Amount', 0))
        phone         = data.get('MSISDN') or data.get('PhoneNumber', '')
        account_ref   = data.get('BillRefNumber') or data.get('AccountReference', '')
        receipt       = data.get('TransID') or data.get('MpesaReceiptNumber', '')
        trans_time    = data.get('TransTime', '')

        if not amount or not account_ref:
            logger.warning(f'C2B: missing amount or account ref — {data}')
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        # Find loan by account reference (Loan ID or customer UID)
        from apps.loans.models import Loan
        from apps.payments.models import Payment, MpesaTransaction
        from django.utils import timezone

        loan = (Loan.objects.filter(loan_id__iexact=account_ref.strip()).first() or
                Loan.objects.filter(customer__uid__iexact=account_ref.strip(),
                                    status='ACTIVE').first())

        if not loan:
            # Log unmatched payment — cashier will match manually
            logger.warning(f'C2B: no loan found for account ref "{account_ref}" — KES {amount} from {phone}')
            MpesaTransaction.objects.create(
                txn_type='C2B', phone=phone, amount=amount,
                mpesa_receipt=receipt, status='UNMATCHED',
                result_desc=f'No loan found for: {account_ref}',
                initiated_at=timezone.now(),
            )
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted — logged as unmatched'})

        if loan.status not in ('ACTIVE', 'DEFAULT'):
            logger.info(f'C2B: loan {loan.loan_id} status={loan.status} — payment logged')

        # Record payment
        payment = Payment.objects.create(
            loan         = loan,
            amount       = amount,
            method       = 'MPESA',
            payment_type = 'FULL' if amount >= float(loan.balance) else 'PARTIAL',
            mpesa_ref    = receipt,
            phone        = phone,
            paid_at      = timezone.now(),
        )

        # Record M-Pesa transaction log
        MpesaTransaction.objects.create(
            txn_type     = 'C2B',
            phone        = phone,
            amount       = amount,
            loan         = loan,
            mpesa_receipt= receipt,
            status       = 'SUCCESS',
            completed_at = timezone.now(),
            initiated_at = timezone.now(),
        )

        # Fire notifications
        try:
            from apps.notifications.tasks import task_sms_payment_confirmed, task_email_payment_received
            task_sms_payment_confirmed.delay(payment.id)
            task_email_payment_received.delay(payment.id)
        except Exception:
            pass

        logger.info(f'C2B: Payment {payment.ref} recorded — {loan.loan_id} KES {amount} from {phone}')
        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})


class MpesaC2BValidationView(APIView):
    """
    POST /api/v1/payments/mpesa/c2b/validate/
    Daraja calls this BEFORE processing — we can reject invalid account refs.
    """
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        account_ref = (request.data.get('BillRefNumber') or
                       request.data.get('AccountReference', '')).strip()
        from apps.loans.models import Loan
        from apps.customers.models import Customer

        # Accept if valid loan ID or customer UID
        valid = (Loan.objects.filter(loan_id__iexact=account_ref, status='ACTIVE').exists() or
                 Customer.objects.filter(uid__iexact=account_ref, status='ACTIVE').exists())

        if valid:
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        else:
            # Still accept — log as unmatched rather than reject
            # (rejecting causes friction for cashiers manually reconciling)
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})


class PrivilegedPaymentUploadView(APIView):
    """
    POST /api/v1/payments/upload/
    Direct payment posting for Admin, HOP, GM, Branch Manager.
    Bypasses the normal loan officer flow — used for:
      - Correcting M-Pesa mismatches
      - Posting bank transfers centrally
      - Backdating (with override)
      - Bulk import from Excel/CSV

    Required fields: loan_id (or loan pk), amount, method, date
    Optional: notes, mpesa_ref, override_date (Admin/HOP only)
    """
    permission_classes = [CanUploadPayment]

    def post(self, request):
        from apps.loans.models import Loan
        from apps.payments.models import Payment
        from apps.payments.serializers import PaymentSerializer
        from apps.accounts.models import AuditLog
        from decimal import Decimal
        import datetime

        # Resolve loan
        loan_id  = request.data.get('loan_id', '').strip()
        loan_pk  = request.data.get('loan',    None)
        amount   = request.data.get('amount',  0)
        method   = request.data.get('method',  'CASH')
        mpesa_ref= request.data.get('mpesa_ref', '')
        notes    = request.data.get('notes',   '')
        pay_date = request.data.get('date',    None)  # YYYY-MM-DD (Admin/HOP can backdate)

        if not amount or float(amount) <= 0:
            return Response({'detail': 'amount must be a positive number.'}, status=400)

        try:
            if loan_pk:
                loan = Loan.objects.get(pk=loan_pk)
            elif loan_id:
                loan = Loan.objects.get(loan_id__iexact=loan_id)
            else:
                return Response({'detail': 'Provide loan (pk) or loan_id.'}, status=400)
        except Loan.DoesNotExist:
            return Response({'detail': f'Loan {loan_id or loan_pk} not found.'}, status=404)

        if loan.status not in ('ACTIVE', 'DEFAULT', 'APPROVED'):
            return Response(
                {'detail': f'Cannot post payment to loan with status: {loan.status}.'},
                status=400,
            )

        # Resolve payment date
        paid_at = timezone.now()
        if pay_date:
            try:
                paid_at = datetime.datetime.combine(
                    datetime.date.fromisoformat(pay_date),
                    datetime.time(12, 0),
                    tzinfo=timezone.get_current_timezone(),
                )
                # Only Admin / Super Admin / HOP / GM can backdate
                allowed_backdate = {User.Role.SUPER_ADMIN, User.Role.HOP, User.Role.GM}
                if (request.user.role not in allowed_backdate
                        and not request.user.is_superuser
                        and paid_at.date() < timezone.now().date()):
                    return Response(
                        {'detail': 'Only Admin, HOP, or GM can backdate payments.'},
                        status=403,
                    )
            except ValueError:
                return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        amt = Decimal(str(amount))
        payment = Payment.objects.create(
            loan         = loan,
            amount       = amt,
            method       = method,
            payment_type = 'FULL' if amt >= loan.balance else 'PARTIAL',
            mpesa_ref    = mpesa_ref,
            phone        = loan.customer.phone,
            recorded_by  = request.user,
            paid_at      = paid_at,
            notes        = (
                f'[PRIVILEGED UPLOAD by {request.user.full_name} ({request.user.role})] '
                + (notes or '')
            ),
        )

        # Auto-post to GL
        try:
            from apps.accounting.gl_service import post_payment_received
            post_payment_received(payment, user=request.user)
        except Exception:
            pass

        # Tier recalculation if loan just closed
        try:
            payment.loan.refresh_from_db()
            if payment.loan.status == 'CLOSED':
                from apps.loans.pricing import recalculate_and_save_tier
                recalculate_and_save_tier(loan.customer, user=request.user)
        except Exception:
            pass

        # Audit trail
        AuditLog.objects.create(
            user=request.user,
            action='Privileged Payment Upload',
            model_name='Payment',
            object_id=str(payment.id),
            details={
                'loan_id':  loan.loan_id,
                'amount':   float(amt),
                'method':   method,
                'paid_at':  paid_at.isoformat(),
                'mpesa_ref': mpesa_ref,
                'notes':    notes,
            },
        )

        return Response({
            'detail':     f'Payment {payment.ref} posted to {loan.loan_id}.',
            'payment_ref': payment.ref,
            'loan_id':    loan.loan_id,
            'amount':     float(payment.amount),
            'new_balance': float(loan.balance),
            'loan_status': loan.status,
        }, status=201)


class BulkPaymentUploadView(APIView):
    """
    POST /api/v1/payments/bulk-upload/
    Upload multiple payments from CSV or JSON array.
    Admin, HOP, GM only.

    JSON body: { "payments": [{loan_id, amount, method, date?, mpesa_ref?}, ...] }
    """
    permission_classes = [CanUploadPayment]
    parser_classes = [
        rest_framework.parsers.JSONParser,
        rest_framework.parsers.MultiPartParser,
    ]

    def post(self, request):
        import rest_framework.parsers, csv, io
        from apps.loans.models import Loan
        from apps.payments.models import Payment
        from decimal import Decimal

        # Handle both JSON and CSV upload
        if 'file' in request.FILES:
            file_obj = request.FILES['file']
            content  = file_obj.read().decode('utf-8-sig')
            reader   = csv.DictReader(io.StringIO(content))
            payments_data = []
            for row in reader:
                row = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items()}
                payments_data.append(row)
        else:
            payments_data = request.data.get('payments', [])

        if not payments_data:
            return Response({'detail': 'No payment data provided.'}, status=400)

        created = []
        errors  = []

        for i, row in enumerate(payments_data, 1):
            loan_id  = str(row.get('loan_id', '')).strip()
            amount   = row.get('amount', 0)
            method   = str(row.get('method', 'CASH')).upper()
            mpesa_ref= str(row.get('mpesa_ref', ''))
            notes    = str(row.get('notes', ''))

            if not loan_id or not amount:
                errors.append({'row': i, 'error': 'loan_id and amount required'})
                continue
            try:
                loan = Loan.objects.get(loan_id__iexact=loan_id)
            except Loan.DoesNotExist:
                errors.append({'row': i, 'error': f'Loan {loan_id} not found'})
                continue

            if loan.status not in ('ACTIVE', 'DEFAULT'):
                errors.append({'row': i, 'error': f'Loan {loan_id} status={loan.status}'})
                continue

            try:
                amt = Decimal(str(amount))
                payment = Payment.objects.create(
                    loan=loan, amount=amt, method=method,
                    payment_type='FULL' if amt >= loan.balance else 'PARTIAL',
                    mpesa_ref=mpesa_ref, phone=loan.customer.phone,
                    recorded_by=request.user, paid_at=timezone.now(),
                    notes=f'[BULK UPLOAD row {i} by {request.user.full_name}] {notes}',
                )
                created.append({'row': i, 'loan_id': loan_id, 'ref': payment.ref, 'amount': float(amt)})

                # GL posting
                try:
                    from apps.accounting.gl_service import post_payment_received
                    post_payment_received(payment, user=request.user)
                except Exception:
                    pass

            except Exception as e:
                errors.append({'row': i, 'error': str(e)})

        return Response({
            'created':     len(created),
            'errors':      len(errors),
            'payments':    created,
            'error_detail': errors,
        }, status=200 if not errors else 207)


class PaymentReversalView(APIView):
    """
    POST /api/v1/payments/<pk>/reverse/
    Reverse (cancel) a payment. Admin / HOP / GM only.
    Creates a negative correction journal entry and restores the loan balance.
    """
    permission_classes = [CanUploadPayment]

    def post(self, request, pk):
        from apps.payments.models import Payment
        from apps.accounts.models import AuditLog
        from decimal import Decimal

        try:
            payment = Payment.objects.select_related('loan').get(pk=pk)
        except Payment.DoesNotExist:
            return Response({'detail': 'Payment not found.'}, status=404)

        if payment.is_reversed:
            return Response({'detail': 'Payment has already been reversed.'}, status=400)

        reason = request.data.get('reason', '').strip()
        if not reason:
            return Response({'detail': 'A reason is required for payment reversal.'}, status=400)

        loan = payment.loan
        amt  = payment.amount

        # Mark payment as reversed
        payment.is_reversed   = True
        payment.reversal_reason = reason
        payment.reversed_by   = request.user
        payment.reversed_at   = timezone.now()
        payment.save(update_fields=[
            'is_reversed', 'reversal_reason', 'reversed_by', 'reversed_at'
        ])

        # Restore loan balance
        if loan:
            loan.balance    = (loan.balance or Decimal('0')) + amt
            loan.total_paid = max((loan.total_paid or Decimal('0')) - amt, Decimal('0'))
            if loan.status == 'CLOSED' and loan.balance > 0:
                loan.status = 'ACTIVE'
                loan.closed_at = None
            loan.save(update_fields=['balance', 'total_paid', 'status', 'closed_at'])

        # GL reversal entry
        try:
            from apps.accounting.gl_service import post_payment_reversal
            post_payment_reversal(payment, user=request.user)
        except Exception:
            pass

        # Audit
        AuditLog.objects.create(
            user=request.user,
            action='Payment Reversal',
            model_name='Payment',
            object_id=str(payment.id),
            details={
                'ref':     payment.ref,
                'amount':  float(amt),
                'loan_id': loan.loan_id if loan else None,
                'reason':  reason,
            },
        )

        return Response({
            'detail':       f'Payment {payment.ref} reversed successfully.',
            'payment_ref':  payment.ref,
            'amount':       float(amt),
            'loan_balance': float(loan.balance) if loan else None,
            'loan_status':  loan.status if loan else None,
        })


class MpesaTokenTestView(APIView):
    """
    GET /api/v1/payments/mpesa/test-token/
    Test Daraja credentials by fetching an access token.
    Returns success + token preview, or the Daraja error.
    """
    def get(self, request):
        try:
            from .mpesa import get_access_token
            from django.conf import settings as _s
            token = get_access_token()
            return Response({
                'status':    'success',
                'token':     token[:12] + '...',
                'env':       getattr(_s, 'MPESA_ENV', 'sandbox'),
                'shortcode': getattr(_s, 'MPESA_SHORTCODE', ''),
                'detail':    '✓ Daraja credentials are valid. Access token obtained.',
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'detail': f'Daraja error: {str(e)}',
            }, status=400)
