"""POST /api/auth/password/change/ (change password from profile settings)."""

from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.token_utils import REFRESH_COOKIE_NAME
from mysite.users.models import User

OLD_PASSWORD = "Old-Passw0rd!"
NEW_PASSWORD = "Fresh-Lantern-42"


class PasswordChangeViewTests(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.user = User.objects.create_user(
            email="changer@example.com", password=OLD_PASSWORD, first_name="Casey", last_name="Changer"
        )
        self.client = APIClient()

    def _login(self, client=None, password=OLD_PASSWORD, **extra):
        client = client or APIClient()
        response = client.post(
            reverse("auth-login"), {"email": self.user.email, "password": password}, format="json", **extra
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['data']['tokens']['access']}")
        return client, response.cookies[REFRESH_COOKIE_NAME].value

    def _change(self, client, current=OLD_PASSWORD, new=NEW_PASSWORD, confirm=None, **extra):
        return client.post(
            reverse("auth-password-change"),
            {"current_password": current, "password": new, "password_confirm": new if confirm is None else confirm},
            format="json",
            **extra,
        )

    def _refresh(self, refresh_token):
        client = APIClient()
        client.cookies[REFRESH_COOKIE_NAME] = refresh_token
        return client.post(reverse("auth-token-refresh"))

    @staticmethod
    def _field_messages(response):
        return {(m.get("context") or {}).get("field"): m["i18n_key"] for m in response.json()["messages"]}

    def test_success_changes_password_and_returns_new_tokens(self):
        client, _ = self._login()

        response = self._change(client)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body["data"]["tokens"]["access"])
        self.assertEqual(body["messages"], [{"i18n_key": "notifications.auth.password_updated"}])
        self.assertNotIn("refresh", body["data"]["tokens"])
        cookie = response.cookies[REFRESH_COOKIE_NAME]
        self.assertTrue(cookie.value)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["path"], "/api/auth/token/refresh/")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self._login(password=NEW_PASSWORD)

    def test_revokes_every_refresh_token_but_keeps_this_device_signed_in(self):
        this_device, this_refresh = self._login()
        _, other_refresh = self._login()

        response = self._change(this_device)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self._refresh(other_refresh).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self._refresh(this_refresh).status_code, status.HTTP_401_UNAUTHORIZED)
        new_refresh = response.cookies[REFRESH_COOKIE_NAME].value
        self.assertEqual(self._refresh(new_refresh).status_code, status.HTTP_200_OK)

        # The access token returned in the body works for the next request.
        this_device.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['data']['tokens']['access']}")
        self.assertEqual(this_device.get(reverse("user-profile")).status_code, status.HTTP_200_OK)

    def test_success_emails_security_notice(self):
        client, _ = self._login()

        response = self._change(client, REMOTE_ADDR="203.0.113.9")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.user.email])
        self.assertEqual(message.subject, "Your password was changed")
        self.assertIn("Casey", message.body)
        self.assertIn("203.0.113.9", message.body)
        self.assertIn("http://localhost:3000/password/reset/request", message.body)
        self.assertNotIn(NEW_PASSWORD, message.body)

    @patch("mysite.auth.views.passwords.send_email_task.delay", side_effect=RuntimeError("broker down"))
    def test_email_failure_does_not_fail_the_change(self, _mock_delay):
        self.client.force_authenticate(self.user)

        response = self._change(self.client)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_wrong_current_password(self):
        self.client.force_authenticate(self.user)

        response = self._change(self.client, current="not-my-password")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"], "validation_failed")
        self.assertEqual(self._field_messages(response), {"current_password": "errors.auth.invalid_password"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))
        self.assertEqual(mail.outbox, [])

    def test_password_validators_run(self):
        self.client.force_authenticate(self.user)
        cases = {
            "Sh0rt!": "errors.password_too_short",
            "password1": "errors.password_too_common",
            "84629173550": "errors.password_entirely_numeric",
            "changer@example.com": "errors.password_too_similar",
        }
        for password, expected in cases.items():
            with self.subTest(password=password):
                response = self._change(self.client, new=password)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                keys = [m["i18n_key"] for m in response.json()["messages"] if m["context"]["field"] == "password"]
                self.assertIn(expected, keys)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))

    def test_too_short_reports_minimum_length(self):
        self.client.force_authenticate(self.user)

        response = self._change(self.client, new="Sh0rt!")

        message = next(m for m in response.json()["messages"] if m["i18n_key"] == "errors.password_too_short")
        self.assertEqual(str(message["context"]["minLength"]), "8")
        self.assertEqual(message["context"]["field"], "password")

    def test_confirmation_mismatch(self):
        self.client.force_authenticate(self.user)

        response = self._change(self.client, confirm="Something-Else-77")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._field_messages(response), {"password_confirm": "errors.password_mismatch"})

    def test_unauthenticated_is_401(self):
        response = self._change(APIClient())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))

    def test_account_without_usable_password_must_use_reset_flow(self):
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("auth-password-change"),
            {"password": NEW_PASSWORD, "password_confirm": NEW_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"error": "password_not_set", "messages": [{"i18n_key": "errors.auth.password_not_set"}]},
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(mail.outbox, [])

    def test_profile_reports_whether_a_password_is_set(self):
        self.client.force_authenticate(self.user)
        self.assertTrue(self.client.get(reverse("user-profile")).json()["data"]["user"]["has_usable_password"])

        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.assertFalse(self.client.get(reverse("user-profile")).json()["data"]["user"]["has_usable_password"])

    @override_settings(RATELIMIT_ENABLE=True, PASSWORD_CHANGE_RATELIMIT="2/m")
    def test_rate_limited_per_user_across_ips(self):
        self.client.force_authenticate(self.user)
        for ip in ("198.51.100.1", "198.51.100.2"):
            response = self._change(self.client, current="wrong-guess", REMOTE_ADDR=ip)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Third attempt, new IP, correct password: still blocked by the per-user limit.
        limited = self._change(self.client, REMOTE_ADDR="198.51.100.3")

        self.assertEqual(limited.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(
            limited.json(),
            {"error": "rate_limit_exceeded", "messages": [{"i18n_key": "errors.password_change_rate_limit"}]},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))

    @override_settings(RATELIMIT_ENABLE=True, PASSWORD_CHANGE_RATELIMIT="2/m")
    def test_rate_limited_per_ip_across_users(self):
        for index in range(2):
            other = User.objects.create_user(email=f"other{index}@example.com", password=OLD_PASSWORD)
            client = APIClient()
            client.force_authenticate(other)
            self.assertEqual(
                self._change(client, current="wrong-guess", REMOTE_ADDR="198.51.100.7").status_code,
                status.HTTP_400_BAD_REQUEST,
            )

        self.client.force_authenticate(self.user)
        limited = self._change(self.client, REMOTE_ADDR="198.51.100.7")

        self.assertEqual(limited.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
