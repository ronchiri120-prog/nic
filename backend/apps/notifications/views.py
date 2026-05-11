"""notifications/views.py — SMS & Email log endpoints + manual send."""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.accounts.permissions import IsBranchManagerOrAbove, IsSuperAdmin, IsLoanOfficerOrAbove
from .models import SMSLog, EmailLog
from .serializers import SMSLogSerializer, EmailLogSerializer


class SMSLogListView(generics.ListAPIView):
    """View all sent SMS messages."""
    serializer_class  = SMSLogSerializer
    permission_classes = [IsLoanOfficerOrAbove]
    filterset_fields   = ["status", "template"]
    search_fields      = ["recipient", "loan__loan_id", "customer__first_name"]
    
    def get_queryset(self):
        user = self.request.user
        qs = SMSLog.objects.select_related("customer", "loan").all()
        # Loan Officer and BDO can only see SMS logs for their own branch/customers
        if user.role == 'LOAN_OFFICER' or user.role == 'BDO':
            qs = qs.filter(loan__loan_officer=user)
        return qs


class EmailLogListView(generics.ListAPIView):
    """View all sent emails."""
    serializer_class  = EmailLogSerializer
    permission_classes = [IsSuperAdmin]
    queryset = EmailLog.objects.all()


class SendSMSView(APIView):
    """Manually send an SMS to any phone number (admin only)."""
    permission_classes = [IsBranchManagerOrAbove]

    def post(self, request):
        phone    = request.data.get("phone")
        message  = request.data.get("message")
        loan_id  = request.data.get("loan_id")

        if not phone or not message:
            return Response({"detail": "phone and message are required."}, status=400)

        from .sms import send_sms
        loan = None
        if loan_id:
            from apps.loans.models import Loan
            loan = Loan.objects.filter(loan_id=loan_id).first()

        result = send_sms(phone, message, loan=loan, template_key="CUSTOM")
        return Response(result, status=200 if result.get("success") else 500)


class ResendSMSView(APIView):
    """Retry a failed SMS."""
    permission_classes = [IsBranchManagerOrAbove]

    def post(self, request, pk):
        try:
            log = SMSLog.objects.get(pk=pk, status=SMSLog.Status.FAILED)
        except SMSLog.DoesNotExist:
            return Response({"detail": "SMS log not found or not in FAILED state."}, status=404)

        from .sms import send_sms
        result = send_sms(log.recipient, log.message, customer=log.customer,
                          loan=log.loan, template_key=log.template)
        return Response(result)


class NotificationStatsView(APIView):
    """Dashboard stats for notifications - accessible to all authenticated users."""
    permission_classes = []

    def get(self, request):
        from django.db.models import Count
        from django.utils import timezone
        import datetime

        today = timezone.now().date()
        week_start = today - datetime.timedelta(days=7)

        user = request.user
        sms_qs = SMSLog.objects.filter(created_at__date__gte=week_start)
        # Loan Officer and BDO can only see stats for their own customers
        if user.role == 'LOAN_OFFICER' or user.role == 'BDO':
            sms_qs = sms_qs.filter(loan__loan_officer=user)

        sms_stats = sms_qs.values("status").annotate(count=Count("id"))

        email_stats = EmailLog.objects.filter(
            created_at__date__gte=week_start
        ).values("status").annotate(count=Count("id"))

        return Response({
            "sms": {s["status"]: s["count"] for s in sms_stats},
            "email": {e["status"]: e["count"] for e in email_stats},
            "sms_total_today": SMSLog.objects.filter(created_at__date=today).count(),
            "failed_sms_total": SMSLog.objects.filter(status="FAILED").count(),
        })
