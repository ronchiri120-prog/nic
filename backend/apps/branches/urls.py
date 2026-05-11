from django.urls import path
from .views import (
    RegionDetailView, RegionListCreateView,
    BranchListCreateView, BranchDetailView, SubmarketListView,
)

urlpatterns = [
    path('',            BranchListCreateView.as_view(), name='branch-list'),
    path('<int:pk>/',   BranchDetailView.as_view(),     name='branch-detail'),
    path('regions/<int:pk>/', RegionDetailView.as_view(), name='region-detail'),
    path('regions/',    RegionListCreateView.as_view(),  name='region-list'),
    path('submarkets/', SubmarketListView.as_view(),     name='submarket-list'),
]
