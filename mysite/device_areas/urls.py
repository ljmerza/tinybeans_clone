"""URL configuration for device_areas app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceAreaViewSet, DeviceAreaAssignmentViewSet

router = DefaultRouter()
router.register(r'areas', DeviceAreaViewSet, basename='device-area')
router.register(r'assignments', DeviceAreaAssignmentViewSet, basename='device-area-assignment')

urlpatterns = [
    path('', include(router.urls)),
]
