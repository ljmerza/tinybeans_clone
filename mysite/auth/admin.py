from django.contrib import admin
from .models import (
    TwoFactorSettings,
    TwoFactorCode,
    RecoveryCode,
    TrustedDevice,
    TwoFactorAuditLog,
)


@admin.register(TwoFactorSettings)
class TwoFactorSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_enabled', 'preferred_method', 'created_at']
    list_filter = ['is_enabled', 'preferred_method']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TwoFactorCode)
class TwoFactorCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'method', 'purpose', 'is_used', 'expires_at']
    list_filter = ['is_used', 'method', 'purpose']
    search_fields = ['user__username', 'code']
    readonly_fields = ['created_at']


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code_hash_preview', 'is_used', 'used_at', 'created_at']
    list_filter = ['is_used']
    search_fields = ['user__username']
    readonly_fields = ['code_hash', 'created_at', 'used_at']
    
    def code_hash_preview(self, obj):
        """Show first 8 characters of hash for identification"""
        return f"{obj.code_hash[:8]}..." if obj.code_hash else "-"
    code_hash_preview.short_description = 'Code Hash'


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_name', 'ip_address', 'last_used_at', 'expires_at']
    list_filter = ['expires_at']
    search_fields = ['user__username', 'device_name', 'device_id']
    readonly_fields = ['device_id', 'created_at', 'last_used_at']


@admin.register(TwoFactorAuditLog)
class TwoFactorAuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'method', 'success', 'ip_address', 'created_at']
    list_filter = ['action', 'method', 'success', 'created_at']
    search_fields = ['user__username', 'action', 'ip_address']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

