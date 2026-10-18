"""Admin configuration for API tokens: a read-only list with an emergency revoke."""

from django.contrib import admin, messages

from . import services
from .models import CircleApiToken


@admin.register(CircleApiToken)
class CircleApiTokenAdmin(admin.ModelAdmin):
    """Tokens are created by circle admins in the app (the plaintext is shown only there); never here."""

    list_display = ["name", "circle", "display_prefix", "status", "created_by", "last_used_at", "created_at"]
    list_filter = ["circle", "can_suggest"]
    search_fields = ["name", "display_prefix"]
    exclude = ["token_hash"]
    readonly_fields = [
        "id",
        "circle",
        "created_by",
        "name",
        "display_prefix",
        "can_suggest",
        "expires_at",
        "revoked_at",
        "revoked_by",
        "revoked_reason",
        "last_used_at",
        "last_used_ip",
        "created_at",
    ]
    actions = ["revoke_selected"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Revoke instead, so the row (and who made it) stays.
        return False

    @admin.action(description="Revoke selected API tokens")
    def revoke_selected(self, request, queryset):
        revoked = sum(services.revoke_token(token, by_user=request.user) for token in queryset)
        self.message_user(request, f"Revoked {revoked} token(s).", messages.SUCCESS)
