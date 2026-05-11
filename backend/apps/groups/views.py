"""groups/views.py — Group / Chama Lending endpoints."""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal

from apps.accounts.permissions import IsLoanOfficerOrAbove, CanApproveLoan
from .models import LoanGroup, GroupMembership, GroupLoan, GroupLoanShare
from .serializers import LoanGroupSerializer, GroupMembershipSerializer, GroupLoanSerializer


class LoanGroupListCreateView(generics.ListCreateAPIView):
    serializer_class  = LoanGroupSerializer
    permission_classes = [IsLoanOfficerOrAbove]
    search_fields     = ["name","group_id"]
    filterset_fields  = ["status","branch"]

    def get_queryset(self):
        return LoanGroup.objects.select_related("branch","loan_officer","chairperson").prefetch_related("memberships__customer")

    def perform_create(self, serializer):
        serializer.save(loan_officer=self.request.user, branch=self.request.user.branch)


class LoanGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class  = LoanGroupSerializer
    permission_classes = [IsLoanOfficerOrAbove]
    queryset = LoanGroup.objects.prefetch_related("memberships__customer")


class AddGroupMemberView(APIView):
    permission_classes = [IsLoanOfficerOrAbove]

    def post(self, request, pk):
        try:
            group = LoanGroup.objects.get(pk=pk)
        except LoanGroup.DoesNotExist:
            return Response({"detail": "Group not found."}, status=404)

        if group.member_count >= group.max_members:
            return Response({"detail": f"Group is full ({group.max_members} max)."}, status=400)

        ser = GroupMembershipSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        membership = ser.save(group=group)
        return Response(GroupMembershipSerializer(membership).data, status=201)


class GroupLoanListCreateView(generics.ListCreateAPIView):
    serializer_class  = GroupLoanSerializer
    permission_classes = [IsLoanOfficerOrAbove]
    filterset_fields  = ["status","group"]
    queryset = GroupLoan.objects.select_related("group","product").prefetch_related("shares__member__customer")


class ApproveGroupLoanView(APIView):
    permission_classes = [CanApproveLoan]

    def post(self, request, pk):
        try:
            group_loan = GroupLoan.objects.get(pk=pk, status=GroupLoan.Status.PENDING)
        except GroupLoan.DoesNotExist:
            return Response({"detail": "Not found or not pending."}, status=404)

        group_loan.status      = GroupLoan.Status.APPROVED
        group_loan.approved_by = request.user
        group_loan.approved_at = timezone.now()
        group_loan.save()
        return Response({"detail": f"{group_loan.group_loan_id} approved."})


class DisburseGroupLoanView(APIView):
    """Disburse group loan — creates individual Loan records for each member share."""
    permission_classes = [CanApproveLoan]

    def post(self, request, pk):
        from apps.loans.models import Loan
        import datetime

        try:
            group_loan = GroupLoan.objects.prefetch_related(
                "shares__member__customer"
            ).get(pk=pk, status=GroupLoan.Status.APPROVED)
        except GroupLoan.DoesNotExist:
            return Response({"detail": "Not found or not approved."}, status=404)

        group_loan.status      = GroupLoan.Status.ACTIVE
        group_loan.disbursed_at= timezone.now()
        group_loan.due_date    = (timezone.now() + datetime.timedelta(days=group_loan.tenure_days)).date()
        group_loan.save()

        created_loans = []
        for share in group_loan.shares.all():
            individual_loan = Loan.objects.create(
                customer        = share.member.customer,
                product         = group_loan.product,
                branch          = group_loan.group.branch,
                loan_officer    = group_loan.group.loan_officer,
                principal       = share.amount,
                interest_rate   = group_loan.interest_rate,
                tenure_days     = group_loan.tenure_days,
                status          = "ACTIVE",
                disbursed_at    = timezone.now(),
                due_date        = group_loan.due_date,
                notes           = f"Group loan: {group_loan.group_loan_id}",
            )
            share.individual_loan = individual_loan
            share.balance         = individual_loan.balance
            share.save()
            created_loans.append(individual_loan.loan_id)

        return Response({
            "detail":        f"{group_loan.group_loan_id} disbursed to {len(created_loans)} members.",
            "loans_created": created_loans,
        })
