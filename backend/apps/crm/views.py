"""CRM views for customer interactions"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import CRMInteraction
from .serializers import CRMInteractionSerializer, CRMInteractionListSerializer


class CRMInteractionViewSet(viewsets.ModelViewSet):
    """ViewSet for CRM interactions"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'conversation_method', 'conversation_purpose', 'outcome', 'next_step']
    search_fields = ['customer_name', 'customer_phone', 'outcome_details', 'recording_transcript']
    ordering_fields = ['created_at', 'next_interaction_date', 'ptp_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter by customer if provided, otherwise return all"""
        queryset = CRMInteraction.objects.select_related('customer', 'recorded_by', 'loan')
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset
    
    def get_serializer_class(self):
        """Use list serializer for list actions"""
        if self.action == 'list':
            return CRMInteractionListSerializer
        return CRMInteractionSerializer
    
    @action(detail=False, methods=['get'])
    def by_customer(self, request):
        """Get interactions for a specific customer"""
        customer_id = request.query_params.get('customer_id')
        if not customer_id:
            return Response({'detail': 'customer_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        interactions = self.get_queryset().filter(customer_id=customer_id)
        serializer = CRMInteractionListSerializer(interactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def ptp_today(self, request):
        """Get all PTP records for today"""
        from django.utils import timezone
        from datetime import date
        
        today = date.today()
        interactions = self.get_queryset().filter(
            ptp_date=today,
            outcome='PTP'
        )
        serializer = CRMInteractionListSerializer(interactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def follow_ups(self, request):
        """Get interactions requiring follow-up (next_interaction_date <= today)"""
        from datetime import date
        
        today = date.today()
        interactions = self.get_queryset().filter(
            next_interaction_date__lte=today
        )
        serializer = CRMInteractionListSerializer(interactions, many=True)
        return Response(serializer.data)
