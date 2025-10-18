from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from auth.token_utils import DEFAULT_TOKEN_TTL_SECONDS, delete_token, store_token
from .models import (
    ChildGuardianConsent,
    ChildProfile,
    ChildProfileUpgradeStatus,
    ChildUpgradeAuditLog,
    ChildUpgradeEventType,
    Circle,
    CircleInvitation,
    CircleMembership,
    User,
    UserNotificationPreferences,
)
from emails.tasks import send_email_task
from emails.templates import CHILD_UPGRADE_TEMPLATE


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


class ChildGuardianConsentInline(admin.TabularInline):
    model = ChildGuardianConsent
    extra = 0
    can_delete = False
    readonly_fields = (
        'guardian_name',
        'guardian_relationship',
        'agreement_reference',
        'consent_method',
        'consent_metadata',
        'signed_at',
        'captured_by',
        'created_at',
    )
    ordering = ('-created_at',)


class ChildUpgradeAuditLogInline(admin.TabularInline):
    model = ChildUpgradeAuditLog
    extra = 0
    can_delete = False
    readonly_fields = ('event_type', 'performed_by', 'metadata', 'created_at')
    ordering = ('-created_at',)


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = (
        'display_name',
        'circle',
        'upgrade_status',
        'pending_invite_email',
        'upgrade_token_expires_at',
        'linked_user',
    )
    list_filter = ('upgrade_status', 'circle')
    search_fields = ('display_name',)
    inlines = [ChildGuardianConsentInline, ChildUpgradeAuditLogInline]
    actions = ['resend_upgrade_invite', 'revoke_upgrade_invite']

    @admin.action(description=_('Resend upgrade invitation to selected child profiles'))
    def resend_upgrade_invite(self, request, queryset):
        successes = 0
        skipped = 0
        for child in queryset.select_related('circle'):
            if child.upgrade_status != ChildProfileUpgradeStatus.PENDING or not child.pending_invite_email:
                skipped += 1
                continue

            if child.upgrade_token:
                delete_token('child-upgrade', child.upgrade_token)

            expires_at = (
                timezone.now() + timedelta(seconds=DEFAULT_TOKEN_TTL_SECONDS)
                if DEFAULT_TOKEN_TTL_SECONDS
                else None
            )
            token = store_token(
                'child-upgrade',
                {
                    'child_id': str(child.id),
                    'circle_id': child.circle_id,
                    'email': child.pending_invite_email,
                    'issued_at': timezone.now().isoformat(),
                },
            )
            child.upgrade_token = token
            child.upgrade_token_expires_at = expires_at
            child.upgrade_status = ChildProfileUpgradeStatus.PENDING
            child.save(
                update_fields=[
                    'upgrade_token',
                    'upgrade_token_expires_at',
                    'upgrade_status',
                    'updated_at',
                ]
            )

            send_email_task.delay(
                to_email=child.pending_invite_email,
                template_id=CHILD_UPGRADE_TEMPLATE,
                context={
                    'token': token,
                    'email': child.pending_invite_email,
                    'child_name': child.display_name,
                    'circle_name': child.circle.name,
                },
            )

            consent = child.guardian_consents.order_by('-created_at').first()
            child.log_upgrade_event(
                ChildUpgradeEventType.TOKEN_REISSUED,
                performed_by=request.user,
                metadata={
                    'token': token,
                    'admin_action': 'resend',
                    'consent_id': str(consent.id) if consent else None,
                },
            )
            successes += 1

        if successes:
            self.message_user(
                request,
                _('%(count)s upgrade invitation%(plural)s resent.')
                % {'count': successes, 'plural': '' if successes == 1 else 's'},
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                _('%(count)s profile%(plural)s skipped (not pending or missing email).')
                % {'count': skipped, 'plural': '' if skipped == 1 else 's'},
                level=messages.WARNING,
            )

    @admin.action(description=_('Revoke pending upgrade invitations'))
    def revoke_upgrade_invite(self, request, queryset):
        revoked = 0
        skipped = 0
        for child in queryset.select_related('circle'):
            if not child.upgrade_token and not child.pending_invite_email:
                skipped += 1
                continue

            if child.upgrade_token:
                delete_token('child-upgrade', child.upgrade_token)

            child.pending_invite_email = None
            child.upgrade_token = None
            child.upgrade_token_expires_at = None
            child.upgrade_requested_by = None
            child.upgrade_status = ChildProfileUpgradeStatus.UNLINKED
            child.save(
                update_fields=[
                    'pending_invite_email',
                    'upgrade_token',
                    'upgrade_token_expires_at',
                    'upgrade_requested_by',
                    'upgrade_status',
                    'updated_at',
                ]
            )

            child.log_upgrade_event(
                ChildUpgradeEventType.TOKEN_REVOKED,
                performed_by=request.user,
                metadata={'admin_action': 'revoke'},
            )
            revoked += 1

        if revoked:
            self.message_user(
                request,
                _('%(count)s invitation%(plural)s revoked.')
                % {'count': revoked, 'plural': '' if revoked == 1 else 's'},
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                _('%(count)s profile%(plural)s skipped (no active invitation).')
                % {'count': skipped, 'plural': '' if skipped == 1 else 's'},
                level=messages.WARNING,
            )


@admin.register(UserNotificationPreferences)
class UserNotificationPreferencesAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'circle',
        'notify_new_media',
        'notify_weekly_digest',
        'digest_frequency',
        'push_enabled',
        'channel',
    )
    list_filter = ('channel', 'notify_new_media', 'notify_weekly_digest', 'digest_frequency', 'push_enabled')


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


@admin.register(ChildUpgradeAuditLog)
class ChildUpgradeAuditLogAdmin(admin.ModelAdmin):
    list_display = ('child', 'event_type', 'performed_by', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('child__display_name', 'performed_by__username')
    readonly_fields = ('child', 'event_type', 'performed_by', 'metadata', 'created_at')
    ordering = ('-created_at',)
