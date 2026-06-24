"""Admin interface for device areas."""
from django.contrib import admin
from .models import DeviceArea, DeviceAreaAssignment


@admin.register(DeviceArea)
class DeviceAreaAdmin(admin.ModelAdmin):
    """Admin interface for DeviceArea model."""
    
    list_display = ['name', 'is_default', 'device_count', 'created_at', 'updated_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def device_count(self, obj):
        """Display count of devices in this area."""
        return obj.device_assignments.count()
    device_count.short_description = 'Device Count'


@admin.register(DeviceAreaAssignment)
class DeviceAreaAssignmentAdmin(admin.ModelAdmin):
    """Admin interface for DeviceAreaAssignment model."""
    
    list_display = ['device_name', 'area', 'assigned_by', 'assigned_at', 'updated_at']
    list_filter = ['area', 'assigned_at']
    search_fields = ['device__device_name', 'device__device_id', 'area__name']
    readonly_fields = ['assigned_at', 'updated_at']
    autocomplete_fields = ['device', 'area', 'assigned_by']
    
    def device_name(self, obj):
        """Display device name."""
        return obj.device.device_name
    device_name.short_description = 'Device'
