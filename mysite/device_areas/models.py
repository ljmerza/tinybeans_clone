"""Models for device area management."""
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class DeviceArea(models.Model):
    """Represents a physical area/location where devices can be placed."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Device Area'
        verbose_name_plural = 'Device Areas'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Ensure only one default area exists."""
        if self.is_default:
            # Set all other areas to non-default
            DeviceArea.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class DeviceAreaAssignment(models.Model):
    """Links trusted devices to areas."""
    
    device = models.OneToOneField(
        'auth_app.TrustedDevice',
        on_delete=models.CASCADE,
        related_name='area_assignment'
    )
    area = models.ForeignKey(
        DeviceArea,
        on_delete=models.CASCADE,
        related_name='device_assignments'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='device_assignments_made'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Device Area Assignment'
        verbose_name_plural = 'Device Area Assignments'
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.device.device_name} -> {self.area.name}"
