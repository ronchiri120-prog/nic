from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Asset
from .serializers import AssetSerializer
from apps.accounts.permissions import IsLoanOfficerOrAbove

class AssetListCreateView(generics.ListCreateAPIView):
    serializer_class = AssetSerializer
    filterset_fields = ["category", "customer", "is_active"]
    search_fields    = ["asset_id", "reg_number", "make", "model", "customer__first_name"]
    queryset = Asset.objects.select_related("customer", "loan").all()

class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AssetSerializer
    queryset = Asset.objects.select_related("customer", "loan")


class AssetExportView(APIView):
    """GET /api/v1/assets/export/ — Download asset register as CSV."""
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request):
        import csv
        from django.http import HttpResponse
        qs = Asset.objects.select_related('branch','assigned_to').all()
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="assets.csv"'
        w = csv.writer(resp)
        w.writerow(['Asset ID','Type','Make','Model','Serial','Value','Status','Branch','Officer','Registered'])
        for a in qs:
            w.writerow([
                a.asset_id, a.asset_type, a.make, a.model, a.serial_number,
                a.current_value, a.status,
                a.branch.name if a.branch else '',
                a.assigned_to.full_name if a.assigned_to else '',
                a.created_at.date(),
            ])
        return resp
