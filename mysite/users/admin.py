from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    ChildProfile,
    Circle,
    CircleInvitation,
    CircleMembership,
    User,
    UserNotificationPreferences,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            'Circle Metadata',
            {'fields': ('role', 'email_verified')},
        ),
    )
    list_display = ('username', 'email', 'role', 'is_active', 'email_verified')
    list_filter = ('role', 'is_active', 'email_verified')
    search_fields = ('username', 'email')


class CircleMembershipInline(admin.TabularInline):
    model = CircleMembership
    extra = 0


@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_by', 'created_at')
    search_fields = ('name', 'slug')
    inlines = [CircleMembershipInline]


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'circle', 'upgrade_status', 'linked_user')
    list_filter = ('upgrade_status', 'circle')
    search_fields = ('display_name',)


@admin.register(UserNotificationPreferences)
class UserNotificationPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'circle', 'notify_new_media', 'notify_weekly_digest', 'channel')
    list_filter = ('channel', 'notify_new_media', 'notify_weekly_digest')


@admin.register(CircleMembership)
class CircleMembershipAdmin(admin.ModelAdmin):
    list_display = ('circle', 'user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('circle__name', 'user__username')


@admin.register(CircleInvitation)
class CircleInvitationAdmin(admin.ModelAdmin):
    list_display = ('circle', 'email', 'role', 'status', 'created_at', 'responded_at')
    list_filter = ('status', 'role', 'circle')
    search_fields = ('email',)

