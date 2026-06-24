"""Serializers for device area management."""
from rest_framework import serializers
from .models import DeviceArea, DeviceAreaAssignment


class DeviceAreaSerializer(serializers.ModelSerializer):
    """Serializer for DeviceArea model."""
    
    device_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceArea
        fields = ['id', 'name', 'description', 'is_default', 'device_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'device_count']
    
    def get_device_count(self, obj):
        """Return count of devices assigned to this area."""
        return obj.device_assignments.count()


class DeviceAreaAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for DeviceAreaAssignment model."""
    
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    area_name = serializers.CharField(source='area.name', read_only=True)
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True)
    
    class Meta:
        model = DeviceAreaAssignment
        fields = [
            'id', 'device', 'device_name', 'device_id', 
            'area', 'area_name', 'assigned_by', 'assigned_by_email',
            'assigned_at', 'updated_at'
        ]
        read_only_fields = ['id', 'assigned_by', 'assigned_at', 'updated_at']


class BulkAssignDevicesSerializer(serializers.Serializer):
    """Serializer for bulk assigning devices to an area."""
    
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    area_id = serializers.IntegerField()
    
    def validate_area_id(self, value):
        """Validate that the area exists."""
        if not DeviceArea.objects.filter(id=value).exists():
            raise serializers.ValidationError("Area does not exist.")
        return value
    
    def validate_device_ids(self, value):
        """Validate that devices exist."""
        from mysite.auth.models import TrustedDevice
        existing_count = TrustedDevice.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError("One or more devices do not exist.")
        return value
