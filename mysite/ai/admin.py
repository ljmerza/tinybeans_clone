"""Admin configuration for in-app AI: read-only, except that a superuser can turn a circle off."""

from django.contrib import admin
from django.core.exceptions import PermissionDenied

from mysite.audit import AuditEvent, log_audit_event

from .models import CircleAiSettings


@admin.register(CircleAiSettings)
class CircleAiSettingsAdmin(admin.ModelAdmin):
    """Circle admins turn AI on in the app (accepting the data-sharing notice); here it can only be switched off."""

    list_display = ["circle", "enabled", "last_run_at", "last_success_at", "last_error", "updated_at"]
    list_filter = ["enabled", "last_error"]
    search_fields = ["circle__name", "circle__slug"]
    fields = [
        "circle",
        "enabled",
        "acknowledged_by",
        "acknowledged_at",
        "last_run_at",
        "last_success_at",
        "last_error",
        "updated_by",
        "updated_at",
    ]
    readonly_fields = [field for field in fields if field != "enabled"]

    def get_readonly_fields(self, request, obj=None):
        # Off stays off here: turning it on needs a circle admin's data-sharing acknowledgement.
        if obj is None or not obj.enabled:
            return self.fields
        return self.readonly_fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if obj.enabled and "enabled" in form.changed_data:
            raise PermissionDenied("Only a circle admin can turn AI on.")
        obj.updated_by = request.user
        # Only these, so a scan's status written since the page loaded isn't overwritten.
        obj.save(update_fields=["enabled", "updated_by", "updated_at"])
        if "enabled" in form.changed_data:
            log_audit_event(
                AuditEvent(
                    action="circle.ai_settings.update",
                    actor_type="user",
                    actor_id=str(request.user.pk),
                    target_type="circle",
                    target_id=str(obj.circle_id),
                    metadata={"fields": ["enabled"], "via": "django_admin"},
                )
            )
