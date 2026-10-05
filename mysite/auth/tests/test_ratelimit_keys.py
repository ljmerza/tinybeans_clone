"""Per-account rate limits on the unauthenticated auth endpoints.

These endpoints are also limited per client IP. The per-account limits key on a
field of the JSON body (email or token). django-ratelimit's ``post:<field>``
reads ``request.POST``, which is empty for JSON, so every caller used to land in
one shared bucket: one person's attempts limited everyone and no single account
had a limit of its own. Each request below comes from a fresh IP so only the
per-account limit is in play.
"""

from itertools import count
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIClient

from mysite.auth.token_utils import store_token
from mysite.auth.views.constants import body_field_key
from mysite.users.models import User

PASSWORD = "Sup3r-secret-pw"
LIMITED = {status.HTTP_403_FORBIDDEN, status.HTTP_429_TOO_MANY_REQUESTS}

_ips = count(1)


def fresh_ip():
    return f"198.51.100.{next(_ips) % 250 + 1}"


class BodyFieldKeyTests(TestCase):
    def _drf_request(self, body):
        django_request = RequestFactory().post("/x/", body, content_type="application/json")
        return Request(django_request, parsers=[JSONParser()])

    def test_reads_and_normalises_the_json_body(self):
        key = body_field_key("email")

        self.assertEqual(key("g", self._drf_request({"email": "  Someone@Example.COM "})), "someone@example.com")

    def test_reads_a_plain_django_json_request(self):
        request = RequestFactory().post("/x/", {"token": " abc "}, content_type="application/json")

        self.assertEqual(body_field_key("token")("g", request), "abc")

    def test_reads_form_posts(self):
        request = RequestFactory().post("/x/", {"email": "Form@Example.com"})

        self.assertEqual(body_field_key("email")("g", request), "form@example.com")

    def test_missing_or_unparseable_values_never_raise(self):
        key = body_field_key("email")

        self.assertEqual(key("g", self._drf_request({})), "")
        self.assertEqual(key("g", self._drf_request({"email": ["a@example.com"]})), "")
        bad = RequestFactory().post("/x/", "{not json", content_type="application/json")
        self.assertEqual(key("g", Request(bad, parsers=[JSONParser()])), "")
        self.assertEqual(key("g", bad), "")


@override_settings(RATELIMIT_ENABLE=True)
class LoginRateLimitTests(TestCase):
    # LoginView: 5/h per email (and 10/h per IP).
    def setUp(self):
        cache.clear()
        self.alice = User.objects.create_user(email="alice@example.com", password=PASSWORD)
        self.bob = User.objects.create_user(email="bob@example.com", password=PASSWORD)

    def _login(self, email, password=PASSWORD):
        return APIClient().post(
            reverse("auth-login"), {"email": email, "password": password}, format="json", REMOTE_ADDR=fresh_ip()
        )

    def test_one_accounts_failures_do_not_limit_another_account(self):
        for _ in range(6):
            self._login("alice@example.com", "wrong-guess")

        self.assertIn(self._login("alice@example.com").status_code, LIMITED)
        self.assertEqual(self._login("bob@example.com").status_code, status.HTTP_200_OK)

    def test_each_account_gets_its_own_full_allowance(self):
        for _ in range(3):
            self._login("bob@example.com", "wrong-guess")

        # Case and whitespace variants count against the same account.
        for email in ("alice@example.com", "Alice@Example.com", " alice@example.com", "ALICE@EXAMPLE.COM"):
            self.assertEqual(self._login(email, "wrong-guess").status_code, status.HTTP_400_BAD_REQUEST, email)
        self.assertEqual(self._login("alice@example.com").status_code, status.HTTP_200_OK)

        self.assertIn(self._login("alice@example.com").status_code, LIMITED)


@override_settings(RATELIMIT_ENABLE=True, PASSWORD_RESET_RATELIMIT="2/m")
@patch("mysite.auth.views.passwords.send_email_task.delay")
class PasswordResetRequestRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user(email="alice@example.com", password=PASSWORD)
        User.objects.create_user(email="bob@example.com", password=PASSWORD)

    def _request(self, email):
        return APIClient().post(
            reverse("auth-password-reset-request"), {"email": email}, format="json", REMOTE_ADDR=fresh_ip()
        )

    def test_one_address_does_not_limit_another(self, mock_delay):
        for _ in range(2):
            self.assertEqual(self._request("alice@example.com").status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(self._request("alice@example.com").status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        self.assertEqual(self._request("bob@example.com").status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual([c.kwargs["to_email"] for c in mock_delay.call_args_list][-1], "bob@example.com")

    def test_each_address_gets_its_own_full_allowance(self, mock_delay):
        self.assertEqual(self._request("bob@example.com").status_code, status.HTTP_202_ACCEPTED)

        self.assertEqual(self._request("Alice@Example.com ").status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(self._request("alice@example.com").status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(self._request("ALICE@example.com").status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(mock_delay.call_count, 3)

    def test_ip_limit_still_applies_across_addresses(self, mock_delay):
        client = APIClient()
        url = reverse("auth-password-reset-request")
        for email in ("alice@example.com", "bob@example.com"):
            response = client.post(url, {"email": email}, format="json", REMOTE_ADDR="203.0.113.5")
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        response = client.post(url, {"email": "carol@example.com"}, format="json", REMOTE_ADDR="203.0.113.5")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


@override_settings(RATELIMIT_ENABLE=True)
@patch("mysite.auth.views.send_email_task.delay")
class SignupRateLimitTests(TestCase):
    # SignupView: 3/30m per email (and 5/m per IP).
    def _signup(self, email):
        return APIClient().post(
            reverse("auth-signup"),
            {"email": email, "password": PASSWORD, "first_name": "New", "last_name": "User"},
            format="json",
            REMOTE_ADDR=fresh_ip(),
        )

    def setUp(self):
        cache.clear()

    def test_one_address_does_not_limit_another(self, _mock_delay):
        for _ in range(3):
            self._signup("taken@example.com")
        self.assertEqual(self._signup("taken@example.com").status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        self.assertEqual(self._signup("fresh@example.com").status_code, status.HTTP_201_CREATED)


@override_settings(RATELIMIT_ENABLE=True, PASSWORD_RESET_CONFIRM_RATELIMIT="2/m")
class PasswordResetConfirmRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="alice@example.com", password=PASSWORD)

    def _confirm(self, token, password="Fresh-Lantern-42"):
        return APIClient().post(
            reverse("auth-password-reset-confirm"),
            {"token": token, "password": password, "password_confirm": password},
            format="json",
            REMOTE_ADDR=fresh_ip(),
        )

    def test_guessing_one_token_does_not_limit_another(self):
        for _ in range(2):
            self.assertEqual(self._confirm("guessed-token").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._confirm("guessed-token").status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        token = store_token("password-reset", {"user_id": self.user.id, "issued_at": timezone.now().isoformat()})
        self.assertEqual(self._confirm(token).status_code, status.HTTP_200_OK)


@override_settings(RATELIMIT_ENABLE=True, EMAIL_VERIFICATION_CONFIRM_RATELIMIT="2/m")
class EmailVerificationConfirmRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="alice@example.com", password=PASSWORD)

    def _confirm(self, token):
        return APIClient().post(reverse("auth-verify-confirm"), {"token": token}, format="json", REMOTE_ADDR=fresh_ip())

    def test_guessing_one_token_does_not_limit_another(self):
        for _ in range(2):
            self.assertEqual(self._confirm("guessed-token").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._confirm("guessed-token").status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        token = store_token("verify-email", {"user_id": self.user.id, "issued_at": timezone.now().isoformat()})
        self.assertEqual(self._confirm(token).status_code, status.HTTP_200_OK)
