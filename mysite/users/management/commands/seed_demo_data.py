from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from mysite.users.models import (
    ChildProfile,
    ChildProfileUpgradeStatus,
    Circle,
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
    CircleOnboardingStatus,
    DigestFrequency,
    User,
    UserNotificationPreferences,
    UserRole,
)

DEFAULT_PASSWORD = 'password123'


class Command(BaseCommand):
    help = "Seed a collection of demo circles, users, and child profiles for local development."

    def _mark_verified(self, user: User, onboarding_status: str = CircleOnboardingStatus.COMPLETED) -> None:
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
        if onboarding_status != user.circle_onboarding_status:
            user.set_circle_onboarding_status(onboarding_status, save=True)


    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write(self.style.WARNING('DEBUG is False – seeding demo data in a non-dev environment. Proceeding anyway.'))

        with transaction.atomic():
            self._create_superuser()
            self._create_primary_circle()
            self._create_secondary_circle()
            self._create_user_without_circle()
            self._ensure_notification_preferences()

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
        self.stdout.write(self.style.NOTICE('Default password for seeded accounts: %s' % DEFAULT_PASSWORD))

    def _create_superuser(self) -> User:
        user, created = User.objects.get_or_create(
            email='superadmin@example.com',
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Super',
                'last_name': 'Admin',
            },
        )
        user.is_staff = True
        user.is_superuser = True
        user.first_name = user.first_name or 'Super'
        user.last_name = user.last_name or 'Admin'
        if created or not user.check_password(DEFAULT_PASSWORD):
            user.set_password(DEFAULT_PASSWORD)
        user.save()
        self._mark_verified(user)
        self.stdout.write('· Superuser available at superadmin@example.com')
        return user

    def _create_primary_circle(self) -> Circle:
        guardian, _ = User.objects.get_or_create(
            email='guardian@example.com',
            defaults={
                'role': UserRole.CIRCLE_ADMIN,
                'first_name': 'Guardian',
                'last_name': 'Admin',
            },
        )
        guardian.role = UserRole.CIRCLE_ADMIN
        guardian.first_name = guardian.first_name or 'Guardian'
        guardian.last_name = guardian.last_name or 'Admin'
        if not guardian.check_password(DEFAULT_PASSWORD):
            guardian.set_password(DEFAULT_PASSWORD)
        guardian.save()
        self._mark_verified(guardian)

        circle, _ = Circle.objects.get_or_create(
            name='Guardian Family',
            defaults={'created_by': guardian},
        )
        if circle.created_by_id != guardian.id:
            circle.created_by = guardian
            circle.save(update_fields=['created_by'])

        CircleMembership.objects.get_or_create(
            user=guardian,
            circle=circle,
            defaults={'role': UserRole.CIRCLE_ADMIN},
        )

        member, _ = User.objects.get_or_create(
            email='member@example.com',
            defaults={
                'role': UserRole.CIRCLE_MEMBER,
                'first_name': 'Family',
                'last_name': 'Member',
            },
        )
        if not member.check_password(DEFAULT_PASSWORD):
            member.set_password(DEFAULT_PASSWORD)
        member.first_name = member.first_name or 'Family'
        member.last_name = member.last_name or 'Member'
        member.role = UserRole.CIRCLE_MEMBER
        member.save()
        self._mark_verified(member)

        CircleMembership.objects.get_or_create(
            user=member,
            circle=circle,
            defaults={'role': UserRole.CIRCLE_MEMBER, 'invited_by': guardian},
        )

        teenager, _ = User.objects.get_or_create(
            email='teen@example.com',
            defaults={
                'role': UserRole.CIRCLE_MEMBER,
                'first_name': 'Teen',
                'last_name': 'Member',
            },
        )
        if not teenager.check_password(DEFAULT_PASSWORD):
            teenager.set_password(DEFAULT_PASSWORD)
        teenager.first_name = teenager.first_name or 'Teen'
        teenager.last_name = teenager.last_name or 'Member'
        teenager.role = UserRole.CIRCLE_MEMBER
        teenager.save()
        self._mark_verified(teenager)

        CircleMembership.objects.get_or_create(
            user=teenager,
            circle=circle,
            defaults={'role': UserRole.CIRCLE_MEMBER, 'invited_by': guardian},
        )

        linked_child, _ = ChildProfile.objects.get_or_create(
            circle=circle,
            display_name='Avery',
            defaults={'pronouns': 'they/them'},
        )
        linked_child.linked_user = teenager
        linked_child.upgrade_status = ChildProfileUpgradeStatus.LINKED
        linked_child.pending_invite_email = None
        linked_child.save()

        pending_child, _ = ChildProfile.objects.get_or_create(
            circle=circle,
            display_name='Milo',
            defaults={'pronouns': 'he/him'},
        )
        pending_child.upgrade_status = ChildProfileUpgradeStatus.PENDING
        pending_child.pending_invite_email = 'milo.guardian@example.com'
        pending_child.upgrade_requested_by = guardian
        pending_child.save()

        young_child, _ = ChildProfile.objects.get_or_create(
            circle=circle,
            display_name='Luna',
            defaults={'pronouns': 'she/her'},
        )
        young_child.upgrade_status = ChildProfileUpgradeStatus.UNLINKED
        young_child.pending_invite_email = None
        young_child.save()

        CircleInvitation.objects.get_or_create(
            circle=circle,
            email='invitee@example.com',
            defaults={
                'invited_by': guardian,
                'role': UserRole.CIRCLE_MEMBER,
                'status': CircleInvitationStatus.PENDING,
            },
        )

        self.stdout.write('· Guardian circle seeded with admin, members, children, and a pending invite')
        return circle

    def _create_secondary_circle(self) -> Circle:
        admin_two, _ = User.objects.get_or_create(
            email='second@example.com',
            defaults={
                'role': UserRole.CIRCLE_ADMIN,
                'first_name': 'Second',
                'last_name': 'Admin',
            },
        )
        if not admin_two.check_password(DEFAULT_PASSWORD):
            admin_two.set_password(DEFAULT_PASSWORD)
        admin_two.first_name = admin_two.first_name or 'Second'
        admin_two.last_name = admin_two.last_name or 'Admin'
        admin_two.role = UserRole.CIRCLE_ADMIN
        admin_two.save()
        self._mark_verified(admin_two)

        circle_two, _ = Circle.objects.get_or_create(
            name='Adventure Club',
            defaults={'created_by': admin_two},
        )
        if circle_two.created_by_id != admin_two.id:
            circle_two.created_by = admin_two
            circle_two.save(update_fields=['created_by'])

        CircleMembership.objects.get_or_create(
            user=admin_two,
            circle=circle_two,
            defaults={'role': UserRole.CIRCLE_ADMIN},
        )

        # This circle intentionally has no children yet
        self.stdout.write('· Adventure Club circle seeded with just the admin')
        return circle_two

    def _create_user_without_circle(self) -> User:
        user, _ = User.objects.get_or_create(
            email='solo@example.com',
            defaults={
                'role': UserRole.CIRCLE_MEMBER,
                'first_name': 'Solo',
                'last_name': 'User',
            },
        )
        if not user.check_password(DEFAULT_PASSWORD):
            user.set_password(DEFAULT_PASSWORD)
        user.first_name = user.first_name or 'Solo'
        user.last_name = user.last_name or 'User'
        user.role = UserRole.CIRCLE_MEMBER
        user.save()

        self.stdout.write('· Added solo user without any circle membership (solo@example.com)')
        return user

    def _ensure_notification_preferences(self) -> None:
        # Set baseline notification preferences for seeded users so API examples are richer
        for user in User.objects.filter(email__in=[
            'guardian@example.com',
            'member@example.com',
            'teen@example.com',
            'solo@example.com',
        ]):
            prefs, _ = UserNotificationPreferences.objects.get_or_create(user=user, circle=None)
            prefs.digest_frequency = DigestFrequency.WEEKLY
            prefs.notify_weekly_digest = True
            prefs.push_enabled = False
            prefs.save()

            # Ensure at least one circle override exists if the user has memberships
            membership = user.notification_preferences.exclude(circle__isnull=True).first()
            if not membership and user.notification_preferences.count() == 1:
                circle_membership = CircleMembership.objects.filter(user=user).select_related('circle').first()
                if circle_membership:
                    UserNotificationPreferences.objects.get_or_create(
                        user=user,
                        circle=circle_membership.circle,
                        defaults={
                            'digest_frequency': DigestFrequency.DAILY,
                            'notify_new_media': True,
                            'notify_weekly_digest': False,
                            'push_enabled': True,
                        },
                    )

        self.stdout.write('· Notification preferences initialised for sample accounts')
