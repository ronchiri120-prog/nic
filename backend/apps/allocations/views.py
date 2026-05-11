from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Allocation
from .serializers import AllocationSerializer

class AllocationListCreateView(generics.ListCreateAPIView):
    serializer_class = AllocationSerializer
    filterset_fields = ["agent", "branch", "is_active"]

    def get_queryset(self):
        return Allocation.objects.select_related("agent", "loan__customer", "branch").all()

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

class SoftReshuffleView(APIView):
    def post(self, request):
        return Response({"detail": "Soft reshuffle complete."})

class HardReshuffleView(APIView):
    def post(self, request):
        return Response({"detail": "Hard reshuffle complete."})
