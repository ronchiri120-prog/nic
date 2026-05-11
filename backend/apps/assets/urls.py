from django.urls import path
from .views import AssetExportView, AssetListCreateView, AssetDetailView

urlpatterns = [
    path("",          AssetListCreateView.as_view(), name="asset-list"),
    path("<int:pk>/", AssetDetailView.as_view(),     name="asset-detail"),
    path('export/', AssetExportView.as_view(), name='asset-export'),
]
