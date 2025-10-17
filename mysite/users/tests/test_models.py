"""Tests for user models, including User, Circle, and related models."""
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from users.models import (
    ChildGuardianConsent,
    ChildProfile,
    ChildProfileUpgradeStatus,
    ChildUpgradeAuditLog,
    ChildUpgradeEventType,
    Circle,
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
    DigestFrequency,
    GuardianConsentMethod,
    NotificationChannel,
    User,
    UserNotificationPreferences,
    UserRole,
    generate_unique_slug,
)


class UserModelTests(TestCase):
    def test_create_user_with_required_fields(self):
        """Test creating a user with minimum required fields."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, UserRole.CIRCLE_MEMBER)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('password123'))

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
        self.assertEqual(user.role, UserRole.CIRCLE_ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_superuser_validation_errors(self):
        """Test that superuser creation validates required permissions."""
        with self.assertRaises(ValueError) as cm:
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpass',
                is_staff=False
            )
        self.assertIn('is_staff=True', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            User.objects.create_superuser(
                username='admin2',
                email='admin2@example.com',
                password='adminpass',
                is_superuser=False
            )
        self.assertIn('is_superuser=True', str(cm.exception))

    def test_user_creation_validation(self):
        """Test user creation with invalid data."""
        with self.assertRaises(ValueError):
            User.objects.create_user(username='', email='test@example.com', password='pass')
        
        with self.assertRaises(ValueError):
            User.objects.create_user(username='test', email='', password='pass')

    def test_email_uniqueness(self):
        """Test that user emails must be unique."""
        User.objects.create_user(username='user1', email='same@example.com', password='pass')
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(username='user2', email='same@example.com', password='pass')

    def test_user_ordering(self):
        """Test that users are ordered by username."""
        User.objects.create_user(username='zebra', email='z@example.com', password='pass')
        User.objects.create_user(username='alpha', email='a@example.com', password='pass')
        User.objects.create_user(username='beta', email='b@example.com', password='pass')
        
        users = list(User.objects.all())
        usernames = [u.username for u in users]
        self.assertEqual(usernames, ['alpha', 'beta', 'zebra'])

    def test_needs_circle_onboarding_default_pending(self):
        user = User.objects.create_user(username='pending', email='pending@example.com', password='password123')
        self.assertEqual(user.circle_onboarding_status, 'pending')
        self.assertTrue(user.needs_circle_onboarding)

    def test_needs_circle_onboarding_completed_after_membership(self):
        user = User.objects.create_user(username='member', email='member@example.com', password='password123')
        circle = Circle.objects.create(name='Family', created_by=user)
        CircleMembership.objects.create(circle=circle, user=user)
        user.refresh_from_db()
        self.assertEqual(user.circle_onboarding_status, 'completed')
        self.assertFalse(user.needs_circle_onboarding)

    def test_set_circle_onboarding_status_updates_timestamp(self):
        user = User.objects.create_user(username='onboard', email='onboard@example.com', password='password123')
        self.assertIsNone(user.circle_onboarding_updated_at)
        changed = user.set_circle_onboarding_status('dismissed', save=True)
        self.assertTrue(changed)
        self.assertEqual(user.circle_onboarding_status, 'dismissed')
        self.assertIsNotNone(user.circle_onboarding_updated_at)

class CircleModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='creator',
            email='creator@example.com',
            password='password123'
        )

    def test_create_circle(self):
        """Test creating a circle."""
        circle = Circle.objects.create(name='Test Family', created_by=self.user)
        
        self.assertEqual(circle.name, 'Test Family')
        self.assertEqual(circle.created_by, self.user)
        self.assertEqual(circle.slug, 'test-family')
        self.assertIsNotNone(circle.created_at)

    def test_circle_slug_generation(self):
        """Test that circle slugs are automatically generated."""
        circle = Circle.objects.create(name='My Amazing Family!', created_by=self.user)
        self.assertEqual(circle.slug, 'my-amazing-family')

    def test_circle_slug_uniqueness(self):
        """Test that circle slugs are unique."""
        Circle.objects.create(name='Family', created_by=self.user)
        circle2 = Circle.objects.create(name='Family', created_by=self.user)
        
        # Second circle should have unique slug
        self.assertEqual(circle2.slug, 'family-1')

    def test_empty_name_slug_generation(self):
        """Test slug generation when name is empty or invalid."""
        circle = Circle.objects.create(name='', created_by=self.user)
        # Should generate random hex slug
        self.assertEqual(len(circle.slug), 12)

    def test_circle_str_representation(self):
        """Test circle string representation."""
        circle = Circle.objects.create(name='Test Family', created_by=self.user)
        self.assertEqual(str(circle), 'Test Family')

    def test_circle_ordering(self):
        """Test that circles are ordered by name."""
        Circle.objects.create(name='Zebra Family', created_by=self.user)
        Circle.objects.create(name='Alpha Family', created_by=self.user)
        Circle.objects.create(name='Beta Family', created_by=self.user)
        
        circles = list(Circle.objects.all())
        names = [c.name for c in circles]
        self.assertEqual(names, ['Alpha Family', 'Beta Family', 'Zebra Family'])


class CircleMembershipModelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='password123'
        )
        self.circle = Circle.objects.create(name='Test Circle', created_by=self.admin)

    def test_create_membership(self):
        """Test creating a circle membership."""
        membership = CircleMembership.objects.create(
            user=self.member,
            circle=self.circle,
            role=UserRole.CIRCLE_MEMBER,
            invited_by=self.admin
        )
        
        self.assertEqual(membership.user, self.member)
        self.assertEqual(membership.circle, self.circle)
        self.assertEqual(membership.role, UserRole.CIRCLE_MEMBER)
        self.assertEqual(membership.invited_by, self.admin)
        self.assertIsNotNone(membership.created_at)

    def test_membership_unique_constraint(self):
        """Test that user can only have one membership per circle."""
        CircleMembership.objects.create(
            user=self.member,
            circle=self.circle,
            role=UserRole.CIRCLE_MEMBER
        )
        
        with self.assertRaises(IntegrityError):
            CircleMembership.objects.create(
                user=self.member,
                circle=self.circle,
                role=UserRole.CIRCLE_ADMIN
            )

    def test_membership_str_representation(self):
        """Test membership string representation."""
        membership = CircleMembership.objects.create(
            user=self.member,
            circle=self.circle,
            role=UserRole.CIRCLE_MEMBER
        )
        expected = f"{self.member} in {self.circle} ({UserRole.CIRCLE_MEMBER})"
        self.assertEqual(str(membership), expected)


class ChildProfileModelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='parent',
            email='parent@example.com',
            password='password123'
        )
        self.circle = Circle.objects.create(name='Family', created_by=self.admin)

    def test_create_child_profile(self):
        """Test creating a child profile."""
        child = ChildProfile.objects.create(
            circle=self.circle,
            display_name='Little One',
            birthdate=date(2015, 5, 10),
            pronouns='they/them'
        )
        
        self.assertEqual(child.display_name, 'Little One')
        self.assertEqual(child.birthdate, date(2015, 5, 10))
        self.assertEqual(child.pronouns, 'they/them')
        self.assertEqual(child.upgrade_status, ChildProfileUpgradeStatus.UNLINKED)
        self.assertIsNone(child.linked_user)

    def test_child_profile_str_representation(self):
        """Test child profile string representation."""
        child = ChildProfile.objects.create(
            circle=self.circle,
            display_name='Little One'
        )
        self.assertEqual(str(child), 'Little One')

    def test_log_upgrade_event(self):
        """Test logging upgrade events."""
        child = ChildProfile.objects.create(
            circle=self.circle,
            display_name='Little One'
        )
        
        child.log_upgrade_event(
            ChildUpgradeEventType.REQUEST_INITIATED,
            performed_by=self.admin,
            metadata={'email': 'parent@example.com'}
        )
        
        log_entry = child.upgrade_audit_logs.first()
        self.assertEqual(log_entry.event_type, ChildUpgradeEventType.REQUEST_INITIATED)
        self.assertEqual(log_entry.performed_by, self.admin)
        self.assertEqual(log_entry.metadata, {'email': 'parent@example.com'})

    def test_clear_upgrade_token(self):
        """Test clearing upgrade token."""
        child = ChildProfile.objects.create(
            circle=self.circle,
            display_name='Little One',
            upgrade_token='abc123',
            upgrade_token_expires_at=timezone.now() + timedelta(hours=1)
        )
        
        child.clear_upgrade_token()
        
        self.assertIsNone(child.upgrade_token)
        self.assertIsNone(child.upgrade_token_expires_at)


class UserNotificationPreferencesModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.circle = Circle.objects.create(name='Family', created_by=self.user)

    def test_create_global_preferences(self):
        """Test creating global notification preferences."""
        prefs = UserNotificationPreferences.objects.create(
            user=self.user,
            notify_new_media=True,
            notify_weekly_digest=False,
            digest_frequency=DigestFrequency.DAILY,
            push_enabled=True
        )
        
        self.assertEqual(prefs.user, self.user)
        self.assertIsNone(prefs.circle)
        self.assertTrue(prefs.notify_new_media)
        self.assertFalse(prefs.notify_weekly_digest)
        self.assertEqual(prefs.digest_frequency, DigestFrequency.DAILY)
        self.assertTrue(prefs.push_enabled)
        self.assertFalse(prefs.is_circle_override)

    def test_create_circle_specific_preferences(self):
        """Test creating circle-specific notification preferences."""
        prefs = UserNotificationPreferences.objects.create(
            user=self.user,
            circle=self.circle,
            notify_new_media=False
        )
        
        self.assertEqual(prefs.circle, self.circle)
        self.assertTrue(prefs.is_circle_override)

    def test_unique_constraint(self):
        """Test unique constraint on user-circle combination."""
        UserNotificationPreferences.objects.create(
            user=self.user,
            circle=self.circle
        )
        
        with self.assertRaises(IntegrityError):
            UserNotificationPreferences.objects.create(
                user=self.user,
                circle=self.circle
            )

    def test_str_representation(self):
        """Test preferences string representation."""
        # Global preferences
        global_prefs = UserNotificationPreferences.objects.create(user=self.user)
        self.assertEqual(str(global_prefs), f"Preferences for {self.user} (all circles)")
        
        # Circle-specific preferences
        circle_prefs = UserNotificationPreferences.objects.create(
            user=self.user,
            circle=self.circle
        )
        self.assertEqual(str(circle_prefs), f"Preferences for {self.user} (Family)")


class CircleInvitationModelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.circle = Circle.objects.create(name='Family', created_by=self.admin)

    def test_create_invitation(self):
        """Test creating a circle invitation."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER
        )
        
        self.assertEqual(invitation.circle, self.circle)
        self.assertEqual(invitation.email, 'invitee@example.com')
        self.assertEqual(invitation.invited_by, self.admin)
        self.assertEqual(invitation.role, UserRole.CIRCLE_MEMBER)
        self.assertEqual(invitation.status, CircleInvitationStatus.PENDING)
        self.assertIsNotNone(invitation.id)  # UUID should be auto-generated
        self.assertIsNone(invitation.responded_at)

    def test_invitation_str_representation(self):
        """Test invitation string representation."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin
        )
        expected = f"Invite invitee@example.com to {self.circle} (pending)"
        self.assertEqual(str(invitation), expected)


class ChildGuardianConsentModelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.circle = Circle.objects.create(name='Family', created_by=self.admin)
        self.child = ChildProfile.objects.create(
            circle=self.circle,
            display_name='Little One'
        )

    def test_create_consent(self):
        """Test creating guardian consent."""
        consent = ChildGuardianConsent.objects.create(
            child=self.child,
            guardian_name='Parent Name',
            guardian_relationship='Mother',
            consent_method=GuardianConsentMethod.DIGITAL_SIGNATURE,
            agreement_reference='AGREEMENT-123',
            consent_metadata={'ip_address': '127.0.0.1'},
            captured_by=self.admin
        )
        
        self.assertEqual(consent.child, self.child)
        self.assertEqual(consent.guardian_name, 'Parent Name')
        self.assertEqual(consent.guardian_relationship, 'Mother')
        self.assertEqual(consent.consent_method, GuardianConsentMethod.DIGITAL_SIGNATURE)
        self.assertEqual(consent.agreement_reference, 'AGREEMENT-123')
        self.assertEqual(consent.consent_metadata, {'ip_address': '127.0.0.1'})
        self.assertEqual(consent.captured_by, self.admin)
        self.assertIsNotNone(consent.signed_at)

    def test_consent_str_representation(self):
        """Test consent string representation."""
        consent = ChildGuardianConsent.objects.create(
            child=self.child,
            guardian_name='Parent Name',
            guardian_relationship='Mother',
            consent_method=GuardianConsentMethod.DIGITAL_SIGNATURE
        )
        expected = "Consent for Little One by Parent Name"
        self.assertEqual(str(consent), expected)


class UtilityFunctionTests(TestCase):
    def testgenerate_unique_slug(self):
        """Test the unique slug generation utility."""
        # Create a circle to test against
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )
        Circle.objects.create(name='Test', created_by=user, slug='test')
        
        # Test unique slug generation
        slug = generate_unique_slug('Test', Circle.objects)
        self.assertEqual(slug, 'test-1')
        
        # Create another with the same base
        Circle.objects.create(name='Test', created_by=user, slug='test-1')
        slug2 = generate_unique_slug('Test', Circle.objects)
        self.assertEqual(slug2, 'test-2')

    def testgenerate_unique_slug_empty_value(self):
        """Test slug generation with empty value."""
        slug = generate_unique_slug('', Circle.objects)
        self.assertEqual(len(slug), 12)
        self.assertTrue(all(c in '0123456789abcdef' for c in slug))