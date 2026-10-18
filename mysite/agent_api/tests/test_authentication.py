"""Token format and storage, the bearer auth matrix, auto-revoke, last-used, kill switch and throttles."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from mysite.agent_api import tokens
from mysite.agent_api.authentication import INVALID_TOKEN_MESSAGE
from mysite.agent_api.models import CircleApiToken, RevokeReason, TokenStatus
from mysite.agent_api.principal import ApiTokenPrincipal
from mysite.agent_api.throttling import AgentReadThrottle
from mysite.circles.models import CircleMembership
from mysite.users.models import User, UserRole

from .helpers import audit_actions, bearer_client, captured_logs, create_token

WHOAMI = reverse("agent_api:whoami")
REALM = 'Bearer realm="circles-agent"'


def assert_rejected(response):
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response["WWW-Authenticate"] == REALM
    assert response.json() == {"detail": INVALID_TOKEN_MESSAGE}


@pytest.mark.django_db
class TestFormatAndStorage:
    def test_plaintext_shape(self, raw, token):
        assert len(raw) == 48
        assert raw.startswith("circ_")
        assert tokens.TOKEN_RE.match(raw)
        assert token.display_prefix == raw[:12]

    def test_no_column_holds_the_plaintext(self, raw, token):
        row = CircleApiToken.objects.filter(pk=token.pk).values().get()
        assert row["token_hash"] == tokens.hash_token(raw)
        for value in row.values():
            assert raw not in str(value)
            assert raw[12:] not in str(value)

    def test_status_is_revoked_then_expired_then_active(self, token):
        assert token.status == TokenStatus.ACTIVE
        token.expires_at = timezone.now() - timedelta(seconds=1)
        assert token.status == TokenStatus.EXPIRED
        token.revoked_at = timezone.now()
        assert token.status == TokenStatus.REVOKED

    def test_tokens_are_unique(self):
        assert len({tokens.generate_token() for _ in range(50)}) == 50


@pytest.mark.django_db
class TestAuthMatrix:
    def test_valid_token(self, agent):
        response = agent.get(WHOAMI)

        assert response.status_code == status.HTTP_200_OK
        assert response["Cache-Control"] == "no-store"

    def test_no_header(self):
        assert_rejected(APIClient().get(WHOAMI))

    def test_jwt(self, admin):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(admin).access_token}")
        assert_rejected(client.get(WHOAMI))

    def test_query_string_token_is_ignored(self, raw):
        assert_rejected(APIClient().get(WHOAMI, {"token": raw}))

    def test_other_scheme(self, raw):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {raw}")
        assert_rejected(client.get(WHOAMI))

    def test_lowercase_scheme_works(self, raw):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"bearer {raw}")
        assert client.get(WHOAMI).status_code == status.HTTP_200_OK

    def test_unknown_token(self):
        assert_rejected(bearer_client(tokens.generate_token()).get(WHOAMI))

    @pytest.mark.parametrize("bad", ["circ_short", "circ_" + "a" * 44, "circ_" + "!" * 43])
    def test_malformed_token(self, bad, django_assert_num_queries):
        with django_assert_num_queries(0):
            assert_rejected(bearer_client(bad).get(WHOAMI))

    def test_revoked(self, raw, token):
        CircleApiToken.objects.filter(pk=token.pk).update(revoked_at=timezone.now())
        assert_rejected(bearer_client(raw).get(WHOAMI))

    def test_expired(self, raw, token):
        CircleApiToken.objects.filter(pk=token.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        assert_rejected(bearer_client(raw).get(WHOAMI))
        token.refresh_from_db()
        assert token.revoked_at is None  # expiry isn't a revocation

    def test_creator_inactive_auto_revokes(self, raw, token, admin):
        User.objects.filter(pk=admin.pk).update(is_active=False)

        assert_rejected(bearer_client(raw).get(WHOAMI))
        token.refresh_from_db()
        assert token.revoked_reason == RevokeReason.CREATOR_INACTIVE
        assert token.revoked_by is None

    def test_creator_unverified_auto_revokes_when_enforced(self, raw, token, admin, settings):
        User.objects.filter(pk=admin.pk).update(email_verified=False)
        settings.EMAIL_VERIFICATION_ENFORCED = True

        assert_rejected(bearer_client(raw).get(WHOAMI))
        token.refresh_from_db()
        assert token.revoked_reason == RevokeReason.CREATOR_UNVERIFIED

    def test_creator_unverified_is_fine_when_not_enforced(self, raw, admin, settings):
        User.objects.filter(pk=admin.pk).update(email_verified=False)
        settings.EMAIL_VERIFICATION_ENFORCED = False

        assert bearer_client(raw).get(WHOAMI).status_code == status.HTTP_200_OK

    def test_creator_demoted_by_queryset_update_auto_revokes(self, raw, token, admin, circle):
        # .update() skips the membership signals; the per-request check still catches it.
        CircleMembership.objects.filter(user=admin, circle=circle).update(role=UserRole.CIRCLE_MEMBER)

        assert_rejected(bearer_client(raw).get(WHOAMI))
        token.refresh_from_db()
        assert token.revoked_reason == RevokeReason.CREATOR_NOT_ADMIN

        # Promoting them again doesn't bring the token back.
        CircleMembership.objects.filter(user=admin, circle=circle).update(role=UserRole.CIRCLE_ADMIN)
        assert_rejected(bearer_client(raw).get(WHOAMI))

    def test_superuser_creator_who_is_not_an_admin(self, circle):
        boss = User.objects.create_superuser(email="boss@example.com", password="Passw0rd!", email_verified=True)
        token, raw = create_token(circle, boss)

        assert_rejected(bearer_client(raw).get(WHOAMI))
        token.refresh_from_db()
        assert token.revoked_reason == RevokeReason.CREATOR_NOT_ADMIN

    def test_auto_revoke_reason_is_set_once(self, raw, token, admin, settings, caplog):
        User.objects.filter(pk=admin.pk).update(is_active=False)
        with captured_logs(caplog, "mysite.audit"):
            bearer_client(raw).get(WHOAMI)
            User.objects.filter(pk=admin.pk).update(is_active=True, email_verified=False)
            settings.EMAIL_VERIFICATION_ENFORCED = True
            bearer_client(raw).get(WHOAMI)

        token.refresh_from_db()
        assert token.revoked_reason == RevokeReason.CREATOR_INACTIVE
        assert audit_actions(caplog).count("api_token.auto_revoke") == 1

    def test_failures_are_logged_with_the_prefix_only(self, raw, token, caplog):
        CircleApiToken.objects.filter(pk=token.pk).update(revoked_at=timezone.now())
        with captured_logs(caplog, "mysite.audit"):
            bearer_client(raw).get(WHOAMI)

        failures = [
            r for r in caplog.records if r.name == "mysite.audit" and r.extra["action"] == "api_token.auth_failed"
        ]
        assert len(failures) == 1
        assert failures[0].extra["metadata"]["reason"] == "revoked"
        assert failures[0].extra["metadata"]["prefix"] == token.display_prefix
        assert failures[0].extra["metadata"]["path"] == WHOAMI


@pytest.mark.django_db
class TestLastUsed:
    def test_recorded_at_most_once_a_minute(self, agent, token):
        agent.get(WHOAMI)
        token.refresh_from_db()
        assert token.last_used_at is not None
        assert token.last_used_ip == "127.0.0.1"

        recent = timezone.now() - timedelta(seconds=30)
        CircleApiToken.objects.filter(pk=token.pk).update(last_used_at=recent)
        agent.get(WHOAMI)
        token.refresh_from_db()
        assert token.last_used_at == recent

        stale = timezone.now() - timedelta(seconds=61)
        CircleApiToken.objects.filter(pk=token.pk).update(last_used_at=stale)
        agent.get(WHOAMI)
        token.refresh_from_db()
        assert token.last_used_at > stale

    def test_no_update_statement_within_the_minute(self, agent):
        agent.get(WHOAMI)

        with CaptureQueriesContext(connection) as queries:
            agent.get(WHOAMI)
        updates = [q["sql"] for q in queries.captured_queries if q["sql"].startswith("UPDATE")]
        assert updates == []


@pytest.mark.django_db
class TestPrincipal:
    def test_pk_and_id_raise(self, token):
        principal = ApiTokenPrincipal(token)
        with pytest.raises(RuntimeError):
            _ = principal.pk
        with pytest.raises(RuntimeError):
            _ = principal.id
        assert principal.is_authenticated is True
        assert principal.is_superuser is False
        assert principal.circle_id == token.circle_id

    @pytest.mark.parametrize(
        ("method", "path", "data", "expected"),
        [
            ("get", "post-list", {"from": "nope"}, status.HTTP_400_BAD_REQUEST),
            ("get", "post-list", {"child": "00000000-0000-0000-0000-000000000000"}, status.HTTP_404_NOT_FOUND),
            ("post", "milestone-suggestion-create", {"post_id": "x"}, status.HTTP_400_BAD_REQUEST),
        ],
    )
    def test_error_paths_render_normally(self, suggest_agent, method, path, data, expected):
        response = getattr(suggest_agent, method)(reverse(f"agent_api:{path}"), data, format="json")

        assert response.status_code == expected
        assert response.json()

    def test_throttled_error_path_renders_normally(self, agent, settings):
        settings.AGENT_API_READ_RATE = "1/hour"
        agent.get(WHOAMI)

        response = agent.get(WHOAMI)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.json()


@pytest.mark.django_db
class TestKillSwitch:
    def test_disabled_is_a_404_without_touching_the_database(self, raw, settings, django_assert_num_queries):
        settings.AGENT_API_ENABLED = False
        client = bearer_client(raw)

        with django_assert_num_queries(0):
            response = client.get(WHOAMI)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_disabled_without_a_token(self, settings):
        settings.AGENT_API_ENABLED = False
        assert APIClient().get(WHOAMI).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestThrottle:
    def test_per_token_read_limit_with_emptied_default_rates(self, circle, admin, settings, monkeypatch):
        # local.py empties DEFAULT_THROTTLE_RATES; the agent throttles don't depend on it.
        monkeypatch.setattr(AgentReadThrottle, "THROTTLE_RATES", {})
        settings.AGENT_API_READ_RATE = "2/hour"
        _, first = create_token(circle, admin, name="One")
        _, second = create_token(circle, admin, name="Two")
        one, two = bearer_client(first), bearer_client(second)

        assert [one.get(WHOAMI).status_code for _ in range(3)] == [200, 200, 429]
        assert two.get(WHOAMI).status_code == status.HTTP_200_OK

    def test_admins_jwt_bucket_is_separate(self, agent, admin, settings):
        settings.AGENT_API_READ_RATE = "1/hour"
        agent.get(WHOAMI)
        assert agent.get(WHOAMI).status_code == status.HTTP_429_TOO_MANY_REQUESTS

        browser = APIClient()
        browser.force_authenticate(admin)
        assert browser.get(reverse("user-profile")).status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAccessLog:
    def test_successful_requests_log_access_without_the_token(self, agent, raw, token, caplog):
        with captured_logs(caplog, "mysite.agent_api"):
            agent.get(WHOAMI)

        records = [r for r in caplog.records if getattr(r, "event", None) == "agent_api.access"]
        assert len(records) == 1
        assert records[0].extra == {
            "token_id": str(token.id),
            "circle_id": token.circle_id,
            "view": "AgentWhoAmIView",
            "status": 200,
        }

    def test_no_log_line_contains_the_plaintext(self, circle, admin, caplog):
        names = ("mysite.audit", "django.request", "mysite.agent_api")
        with captured_logs(caplog, *names):
            token, raw = create_token(circle, admin)
            bearer_client(raw).get(WHOAMI)
            bearer_client(raw).get(reverse("keeps:keep-feed"))  # rejected by JWT auth
            CircleApiToken.objects.filter(pk=token.pk).update(revoked_at=timezone.now())
            bearer_client(raw).get(WHOAMI)

        # Not vacuous: the create, the access line and the failure were all captured.
        assert {"mysite.audit", "mysite.agent_api"} <= {record.name for record in caplog.records}
        assert len(caplog.records) >= 3
        for record in caplog.records:
            text = f"{record.getMessage()} {record.__dict__}"
            assert raw not in text
            assert raw[12:] not in text
