"""CRM URLs for customer interactions"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CRMInteractionViewSet

router = DefaultRouter()
router.register(r'interactions', CRMInteractionViewSet, basename='crm-interaction')

urlpatterns = [
    path('', include(router.urls)),
]
