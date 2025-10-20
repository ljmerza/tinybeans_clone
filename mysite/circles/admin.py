"""Admin registrations for the circles app."""

from django.contrib import admin

from .models import Circle, CircleInvitation, CircleMembership


class CircleMembershipInline(admin.TabularInline):
    model = CircleMembership
    extra = 0


@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_by', 'created_at')
    search_fields = ('name', 'slug')
    inlines = [CircleMembershipInline]


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

