"""branches/views.py"""
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models.deletion import ProtectedError
from apps.accounts.permissions import IsLoanOfficerOrAbove, IsBranchManagerOrAbove
from .models import Branch, Region
from .serializers import BranchSerializer, RegionSerializer


class RegionListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/v1/branches/regions/ — list and create regions."""
    serializer_class   = RegionSerializer
    permission_classes = [IsBranchManagerOrAbove]
    queryset = Region.objects.prefetch_related('branches').order_by('name')


class BranchListCreateView(generics.ListCreateAPIView):
    serializer_class   = BranchSerializer
    permission_classes = [IsLoanOfficerOrAbove]
    search_fields      = ['name', 'code', 'submarket']
    filterset_fields   = ['region', 'is_active']

    def get_queryset(self):
        return Branch.objects.select_related('region', 'manager').order_by('name')


class BranchDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = BranchSerializer
    permission_classes = [IsBranchManagerOrAbove]
    queryset = Branch.objects.select_related('region', 'manager')

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError as e:
            return Response(
                {'detail': 'Cannot delete this branch because it has customers associated with it. Please reassign or delete the customers first.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class SubmarketListView(APIView):
    """GET /api/v1/branches/submarkets/ — distinct submarket values for filtering."""
    permission_classes = [IsLoanOfficerOrAbove]

    def get(self, request):
        region_id = request.query_params.get('region')
        qs = Branch.objects.filter(is_active=True)
        if region_id:
            qs = qs.filter(region_id=region_id)
        submarkets = list(
            qs.exclude(submarket='')
              .values_list('submarket', flat=True)
              .distinct()
              .order_by('submarket')
        )
        return Response({'submarkets': submarkets})


class RegionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE a region."""
    from .serializers import RegionSerializer
    serializer_class = RegionSerializer
    queryset = Region.objects.all()

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError as e:
            return Response(
                {'detail': 'Cannot delete this region because it has branches associated with it. Please reassign or delete the branches first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
