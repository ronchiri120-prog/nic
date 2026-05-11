from django.urls import path
from .views import AllocationListCreateView, SoftReshuffleView, HardReshuffleView

urlpatterns = [
    path("",               AllocationListCreateView.as_view(), name="allocation-list"),
    path("soft-reshuffle/", SoftReshuffleView.as_view(),       name="soft-reshuffle"),
    path("hard-reshuffle/", HardReshuffleView.as_view(),       name="hard-reshuffle"),
]
