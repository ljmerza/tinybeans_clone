from django.contrib import admin
from .models import (
    TwoFactorSettings,
    TwoFactorCode,
    RecoveryCode,
    TrustedDevice,
    TwoFactorAuditLog,
    MagicLoginToken,
    GoogleOAuthState,
)


@admin.register(TwoFactorSettings)
class TwoFactorSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_enabled', 'preferred_method', 'created_at']
    list_filter = ['is_enabled', 'preferred_method']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TwoFactorCode)
class TwoFactorCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code_preview', 'code_hash_preview', 'method', 'purpose', 'is_used', 'expires_at']
    list_filter = ['is_used', 'method', 'purpose']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'code_preview']
    readonly_fields = ['created_at', 'code_hash']

    def code_hash_preview(self, obj):
        return f"{obj.code_hash[:8]}..." if obj.code_hash else '-'
    code_hash_preview.short_description = 'Code Hash'


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code_hash_preview', 'is_used', 'used_at', 'created_at']
    list_filter = ['is_used']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['code_hash', 'created_at', 'used_at']
    
    def code_hash_preview(self, obj):
        """Show first 8 characters of hash for identification"""
        return f"{obj.code_hash[:8]}..." if obj.code_hash else "-"
    code_hash_preview.short_description = 'Code Hash'


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_name', 'ip_address', 'last_used_at', 'expires_at']
    list_filter = ['expires_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'device_name', 'device_id']
    readonly_fields = ['device_id', 'created_at', 'last_used_at']


@admin.register(TwoFactorAuditLog)
class TwoFactorAuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'method', 'success', 'ip_address', 'created_at']
    list_filter = ['action', 'method', 'success', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'action', 'ip_address']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(MagicLoginToken)
class MagicLoginTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_hash_preview', 'is_used', 'expires_at', 'used_at', 'created_at']
    list_filter = ['is_used', 'created_at', 'expires_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'token_hash']
    readonly_fields = ['token_hash', 'created_at', 'used_at']
    exclude = ('token',)
    date_hierarchy = 'created_at'
    
    def token_hash_preview(self, obj):
        """Show first 8 characters of token hash for identification."""
        return f"{obj.token_hash[:8]}..." if obj.token_hash else "-"
    token_hash_preview.short_description = 'Token Hash'


@admin.register(GoogleOAuthState)
class GoogleOAuthStateAdmin(admin.ModelAdmin):
    """Admin interface for Google OAuth state tokens.
    
    Provides security monitoring and debugging capabilities for OAuth flows.
    """
    list_display = [
        'state_token_preview',
        'created_at',
        'expires_at',
        'used_at',
        'is_expired',
        'ip_address',
        'redirect_uri'
    ]
    list_filter = ['created_at', 'expires_at', 'used_at']
    search_fields = ['state_token', 'ip_address', 'redirect_uri']
    readonly_fields = [
        'state_token',
        'code_verifier',
        'nonce',
        'created_at',
        'used_at',
        'ip_address',
        'user_agent',
        'expires_at',
        'redirect_uri'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def state_token_preview(self, obj):
        """Show first 16 characters of state token for identification."""
        return f"{obj.state_token[:16]}..." if obj.state_token else "-"
    state_token_preview.short_description = 'State Token'
    
    def is_expired(self, obj):
        """Show if state token is expired."""
        from django.utils import timezone
        return obj.expires_at < timezone.now()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
    
    def has_add_permission(self, request):
        """Prevent manual creation of OAuth states."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of OAuth states."""
        return False
