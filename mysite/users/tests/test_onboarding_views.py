"""Tests for circle onboarding API views."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import CircleOnboardingStatus, User


class CircleOnboardingStatusViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="status-user",
            email="status@example.com",
            password="StrongPass123",
        )
        self.client.force_authenticate(self.user)

    def test_returns_onboarding_payload(self):
        response = self.client.get(reverse("circle-onboarding-status"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()["data"]
        self.assertEqual(payload["status"], CircleOnboardingStatus.PENDING)
        self.assertTrue(payload["needs_circle_onboarding"])
        self.assertFalse(payload["email_verified"])
        self.assertEqual(payload["memberships_count"], 0)

    def test_updates_when_membership_created(self):
        circle = Circle.objects.create(name="Family", created_by=self.user)
        CircleMembership.objects.create(circle=circle, user=self.user)
        self.user.refresh_from_db()

        response = self.client.get(reverse("circle-onboarding-status"))
        payload = response.json()["data"]
        self.assertEqual(payload["status"], CircleOnboardingStatus.COMPLETED)
        self.assertFalse(payload["needs_circle_onboarding"])
        self.assertEqual(payload["memberships_count"], 1)


class CircleOnboardingSkipViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="skip-user",
            email="skip@example.com",
            password="StrongPass123",
        )
        self.client.force_authenticate(self.user)

    def test_skip_updates_status(self):
        response = self.client.post(reverse("circle-onboarding-skip"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()["data"]
        self.user.refresh_from_db()
        self.assertEqual(payload["status"], CircleOnboardingStatus.DISMISSED)
        self.assertEqual(self.user.circle_onboarding_status, CircleOnboardingStatus.DISMISSED)
        self.assertFalse(payload["needs_circle_onboarding"])

    def test_skip_noop_when_completed(self):
        circle = Circle.objects.create(name="Family", created_by=self.user)
        CircleMembership.objects.create(circle=circle, user=self.user)
        self.user.refresh_from_db()
        response = self.client.post(reverse("circle-onboarding-skip"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()["data"]
        self.assertEqual(payload["status"], CircleOnboardingStatus.COMPLETED)
        self.assertFalse(payload["needs_circle_onboarding"])
