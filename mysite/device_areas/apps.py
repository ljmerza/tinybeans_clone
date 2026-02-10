"""App configuration for device_areas."""
from django.apps import AppConfig


class DeviceAreasConfig(AppConfig):
    """Configuration for the device_areas app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mysite.device_areas'
    verbose_name = 'Device Areas'
