"""documents/views.py — Document generation endpoints."""
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.accounts.permissions import IsLoanOfficerOrAbove
from apps.customers.models import Customer
from apps.loans.models import Loan
import datetime


def _html_response(html: str, filename: str) -> HttpResponse:
    resp = HttpResponse(html, content_type='text/html; charset=utf-8')
    resp['Content-Disposition'] = f'inline; filename="{filename}"'
    return resp


class CustomerStatementView(APIView):
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request, pk):
        try:
            customer = Customer.objects.select_related('branch').get(pk=pk)
        except Customer.DoesNotExist:
            return Response({'detail': 'Customer not found.'}, status=404)

        date_from = request.query_params.get('from')
        date_to   = request.query_params.get('to')
        try:
            df = datetime.date.fromisoformat(date_from) if date_from else None
            dt = datetime.date.fromisoformat(date_to)   if date_to   else None
        except ValueError:
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        from apps.documents.generators import customer_statement
        html = customer_statement(customer, date_from=df, date_to=dt)
        return _html_response(html, f'statement_{customer.uid}.html')


class LoanAgreementView(APIView):
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request, pk):
        try:
            loan = Loan.objects.select_related('customer', 'product', 'branch').get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=404)
        from apps.documents.generators import loan_agreement
        html = loan_agreement(loan)
        return _html_response(html, f'agreement_{loan.loan_id}.html')


class DisbursementLetterView(APIView):
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request, pk):
        try:
            loan = Loan.objects.select_related('customer', 'product').get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=404)
        if loan.status not in ('ACTIVE', 'CLOSED'):
            return Response({'detail': 'Disbursement letter only available for disbursed loans.'}, status=400)
        from apps.documents.generators import disbursement_letter
        html = disbursement_letter(loan)
        return _html_response(html, f'disbursement_{loan.loan_id}.html')


class DemandLetterView(APIView):
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request, pk):
        from django.utils import timezone
        try:
            loan = Loan.objects.select_related('customer', 'product').get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=404)
        if not loan.due_date:
            return Response({'detail': 'Loan has no due date set.'}, status=400)
        days_overdue = (timezone.now().date() - loan.due_date).days
        if days_overdue < 0:
            days_overdue = 0
        from apps.documents.generators import demand_letter
        html = demand_letter(loan, days_overdue)
        return _html_response(html, f'demand_{loan.loan_id}.html')


class LoanScheduleView(APIView):
    """GET /api/v1/documents/loans/<pk>/schedule/ — view or generate schedule."""
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request, pk):
        try:
            loan = Loan.objects.select_related('product').get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=404)

        from apps.loans.models import RepaymentSchedule
        rows = RepaymentSchedule.objects.filter(loan=loan).order_by('due_date')

        if not rows.exists():
            # Auto-generate if not yet created
            from apps.loans.schedule import generate_schedule, save_schedule
            schedule_type = request.query_params.get('type', 'BULLET')
            instalments   = int(request.query_params.get('instalments', 1))
            rows_data = generate_schedule(loan, schedule_type=schedule_type, num_instalments=instalments)
            save_schedule(loan, rows_data)
            rows = RepaymentSchedule.objects.filter(loan=loan).order_by('due_date')

        data = [{
            'installment':   r.installment,
            'due_date':      str(r.due_date),
            'amount_due':    float(r.amount_due),
            'amount_paid':   float(r.amount_paid),
            'balance':       float(r.amount_due - r.amount_paid),
            'is_paid':       r.is_paid,
            'paid_at':       str(r.paid_at) if r.paid_at else None,
        } for r in rows]

        return Response({
            'loan_id':      loan.loan_id,
            'customer':     loan.customer.full_name,
            'principal':    float(loan.principal),
            'total_amount': float(loan.total_amount),
            'tenure_days':  loan.tenure_days,
            'schedule':     data,
        })

    def post(self, request, pk):
        """Regenerate schedule with specified type."""
        try:
            loan = Loan.objects.get(pk=pk)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=404)

        from apps.loans.schedule import generate_schedule, save_schedule
        schedule_type = request.data.get('type', 'BULLET')
        instalments   = int(request.data.get('instalments', 1))

        if schedule_type not in ('BULLET', 'EQUAL', 'REDUCING'):
            return Response({'detail': 'type must be BULLET, EQUAL, or REDUCING'}, status=400)

        rows = generate_schedule(loan, schedule_type=schedule_type, num_instalments=instalments)
        count = save_schedule(loan, rows)
        return Response({'detail': f'{count} schedule rows created.', 'rows': count})


class PaymentReceiptView(APIView):
    """GET /api/v1/documents/payments/<pk>/receipt/ — printable receipt."""
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request, pk):
        try:
            from apps.payments.models import Payment
            payment = Payment.objects.select_related(
                'loan', 'loan__customer', 'loan__product'
            ).get(pk=pk)
        except Payment.DoesNotExist:
            return Response({'detail': 'Payment not found.'}, status=404)

        from apps.documents.generators import payment_receipt
        html = payment_receipt(payment)
        return _html_response(html, f'receipt_{payment.ref}.html')
