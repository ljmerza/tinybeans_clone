"""Views for device area management."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import DeviceArea, DeviceAreaAssignment
from .serializers import (
    DeviceAreaSerializer, 
    DeviceAreaAssignmentSerializer,
    BulkAssignDevicesSerializer
)
from mysite.auth.models import TrustedDevice


class DeviceAreaViewSet(viewsets.ModelViewSet):
    """ViewSet for managing device areas."""
    
    queryset = DeviceArea.objects.all()
    serializer_class = DeviceAreaSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def sync_unassigned(self, request):
        """
        Sync all devices without an area to the default area.
        Creates a default area if it doesn't exist.
        """
        # Get or create default area
        default_area, created = DeviceArea.objects.get_or_create(
            is_default=True,
            defaults={
                'name': 'Default Area',
                'description': 'Default area for unassigned devices'
            }
        )
        
        # Get all devices without area assignments
        unassigned_devices = TrustedDevice.objects.filter(
            area_assignment__isnull=True
        )
        
        # Assign each device to the default area
        assignments_created = 0
        with transaction.atomic():
            for device in unassigned_devices:
                DeviceAreaAssignment.objects.create(
                    device=device,
                    area=default_area,
                    assigned_by=request.user
                )
                assignments_created += 1
        
        return Response({
            'message': f'Synced {assignments_created} devices to {default_area.name}',
            'default_area_id': default_area.id,
            'default_area_name': default_area.name,
            'devices_synced': assignments_created,
            'default_area_created': created
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def assign_devices(self, request, pk=None):
        """Assign multiple devices to this area."""
        area = self.get_object()
        serializer = BulkAssignDevicesSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        device_ids = serializer.validated_data['device_ids']
        devices = TrustedDevice.objects.filter(id__in=device_ids)
        
        assignments_created = 0
        assignments_updated = 0
        
        with transaction.atomic():
            for device in devices:
                assignment, created = DeviceAreaAssignment.objects.update_or_create(
                    device=device,
                    defaults={
                        'area': area,
                        'assigned_by': request.user
                    }
                )
                if created:
                    assignments_created += 1
                else:
                    assignments_updated += 1
        
        return Response({
            'message': f'Assigned {len(device_ids)} devices to {area.name}',
            'area_id': area.id,
            'area_name': area.name,
            'assignments_created': assignments_created,
            'assignments_updated': assignments_updated
        }, status=status.HTTP_200_OK)


class DeviceAreaAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing device area assignments."""
    
    queryset = DeviceAreaAssignment.objects.select_related('device', 'area', 'assigned_by')
    serializer_class = DeviceAreaAssignmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter assignments by user if not staff."""
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            # Regular users can only see their own device assignments
            queryset = queryset.filter(device__user=self.request.user)
        return queryset
    
    def perform_create(self, serializer):
        """Set the assigned_by field to the current user."""
        serializer.save(assigned_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unassigned(self, request):
        """Get all devices without area assignments."""
        unassigned_devices = TrustedDevice.objects.filter(
            area_assignment__isnull=True
        )
        
        if not request.user.is_staff:
            # Regular users can only see their own devices
            unassigned_devices = unassigned_devices.filter(user=request.user)
        
        devices_data = [{
            'id': device.id,
            'device_id': device.device_id,
            'device_name': device.device_name,
            'user_email': device.user.email,
            'last_used_at': device.last_used_at,
            'created_at': device.created_at
        } for device in unassigned_devices]
        
        return Response({
            'count': len(devices_data),
            'devices': devices_data
        }, status=status.HTTP_200_OK)
