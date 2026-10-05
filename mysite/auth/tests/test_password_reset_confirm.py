"""POST /api/auth/password/reset/confirm/ (set a new password from an emailed link)."""

from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.services.oauth.account_linking_service import AccountLinkingService
from mysite.auth.token_utils import REFRESH_COOKIE_NAME, store_token
from mysite.users.models import User

OLD_PASSWORD = "Old-Passw0rd!"
NEW_PASSWORD = "Fresh-Lantern-42"


class PasswordResetConfirmViewTests(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.user = User.objects.create_user(
            email="resetter@example.com", password=OLD_PASSWORD, first_name="Riley", last_name="Resetter"
        )
        self.client = APIClient()

    def _token(self, user=None):
        user = user or self.user
        return store_token("password-reset", {"user_id": user.id, "issued_at": timezone.now().isoformat()})

    def _confirm(self, token, password=NEW_PASSWORD, confirm=None, **extra):
        return self.client.post(
            reverse("auth-password-reset-confirm"),
            {"token": token, "password": password, "password_confirm": password if confirm is None else confirm},
            format="json",
            **extra,
        )

    def _login(self, password=OLD_PASSWORD):
        response = APIClient().post(
            reverse("auth-login"), {"email": self.user.email, "password": password}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.cookies[REFRESH_COOKIE_NAME].value

    def _refresh(self, refresh_token):
        client = APIClient()
        client.cookies[REFRESH_COOKIE_NAME] = refresh_token
        return client.post(reverse("auth-token-refresh"))

    def test_success_keeps_the_response_shape_and_does_not_log_in(self):
        response = self._confirm(self._token())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(), {"data": {}, "messages": [{"i18n_key": "notifications.auth.password_updated"}]}
        )
        self.assertNotIn(REFRESH_COOKIE_NAME, response.cookies)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_token_is_single_use(self):
        token = self._token()
        self.assertEqual(self._confirm(token).status_code, status.HTTP_200_OK)

        response = self._confirm(token, password="Another-Lantern-43")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"], "invalid_token")

    def test_password_validators_run(self):
        token = self._token()
        cases = {
            "Sh0rt!": "errors.password_too_short",
            "password1": "errors.password_too_common",
            "84629173550": "errors.password_entirely_numeric",
            "resetter@example.com": "errors.password_too_similar",
        }
        for password, expected in cases.items():
            with self.subTest(password=password):
                response = self._confirm(token, password=password)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.json()["error"], "validation_failed")
                keys = [m["i18n_key"] for m in response.json()["messages"] if m["context"]["field"] == "password"]
                self.assertIn(expected, keys)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))
        # A rejected password doesn't burn the link; the user can try again.
        self.assertEqual(self._confirm(token).status_code, status.HTTP_200_OK)

    def test_too_short_reports_minimum_length(self):
        response = self._confirm(self._token(), password="Sh0rt!")

        message = next(m for m in response.json()["messages"] if m["i18n_key"] == "errors.password_too_short")
        self.assertEqual(str(message["context"]["minLength"]), "8")
        self.assertEqual(message["context"]["field"], "password")

    def test_confirmation_mismatch(self):
        response = self._confirm(self._token(), confirm="Something-Else-77")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        fields = {m["context"]["field"]: m["i18n_key"] for m in response.json()["messages"]}
        self.assertEqual(fields, {"password_confirm": "errors.password_mismatch"})

    def test_invalid_token(self):
        response = self._confirm("not-a-real-token")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"error": "invalid_token", "messages": [{"i18n_key": "errors.token_invalid_expired"}]},
        )
        self.assertEqual(mail.outbox, [])

    def test_revokes_every_refresh_token(self):
        first = self._login()
        second = self._login()

        self.assertEqual(self._confirm(self._token()).status_code, status.HTTP_200_OK)

        self.assertEqual(self._refresh(first).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self._refresh(second).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self._refresh(self._login(NEW_PASSWORD)).status_code, status.HTTP_200_OK)

    def test_success_emails_reset_notice(self):
        response = self._confirm(self._token(), REMOTE_ADDR="203.0.113.9")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.user.email])
        self.assertEqual(message.subject, "Your password was reset")
        self.assertIn("Riley", message.body)
        self.assertIn("was just reset", message.body)
        self.assertIn("signed out on all your devices", message.body)
        self.assertIn("203.0.113.9", message.body)
        self.assertIn("http://localhost:3000/password/reset/request", message.body)
        self.assertNotIn(NEW_PASSWORD, message.body)
        html = message.alternatives[0][0]
        self.assertIn("Your password was reset", html)
        self.assertNotIn("was changed", html)

    @patch("mysite.auth.views.passwords.send_email_task.delay", side_effect=RuntimeError("broker down"))
    def test_email_failure_does_not_fail_the_reset(self, _mock_delay):
        response = self._confirm(self._token())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_password_user_keeps_its_provider(self):
        self.assertEqual(self._confirm(self._token()).status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.password_login_enabled)
        self.assertEqual(self.user.auth_provider, "manual")


class GoogleOnlyUserResetTests(TestCase):
    """A Google sign-up has no password until it uses the emailed reset link."""

    def setUp(self):
        cache.clear()
        self.user, action = AccountLinkingService().get_or_create_user(
            {"sub": "google-sub-1", "email": "googler@example.com", "given_name": "Gale", "family_name": "Googler"}
        )
        self.assertEqual(action, "created")
        self.assertFalse(self.user.password_login_enabled)
        self.assertFalse(self.user.has_usable_password())
        self.client = APIClient()

    def _reset(self):
        token = store_token("password-reset", {"user_id": self.user.id, "issued_at": timezone.now().isoformat()})
        return self.client.post(
            reverse("auth-password-reset-confirm"),
            {"token": token, "password": NEW_PASSWORD, "password_confirm": NEW_PASSWORD},
            format="json",
        )

    def test_reset_enables_password_login_and_makes_the_account_hybrid(self):
        self.assertEqual(self._reset().status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.has_usable_password())
        self.assertTrue(self.user.password_login_enabled)
        self.assertEqual(self.user.auth_provider, "hybrid")
        self.assertEqual(self.user.google_id, "google-sub-1")
        login = APIClient().post(
            reverse("auth-login"), {"email": self.user.email, "password": NEW_PASSWORD}, format="json"
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_can_unlink_google_after_setting_a_password(self):
        self.assertEqual(self._reset().status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.client.force_authenticate(self.user)

        response = self.client.delete(reverse("auth-google-unlink"), {"password": NEW_PASSWORD}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.google_id)
        self.assertEqual(self.user.auth_provider, "manual")
        self.assertTrue(self.user.password_login_enabled)
