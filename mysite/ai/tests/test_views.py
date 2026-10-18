"""In-app AI settings, connection test and "Scan now": real circle admins only, never any provider detail."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from mysite.agent_api.tests.helpers import audit_actions, bearer_client, captured_logs, create_token
from mysite.ai import prompts, scan
from mysite.ai.models import CircleAiSettings
from mysite.ai.views import CircleAiSettingsTestView, CircleAiSettingsView, CircleMilestoneScanView
from mysite.albums.models import MilestoneSuggestion
from mysite.albums.tests.helpers import make_keep
from mysite.users.models import UserRole

from .helpers import BASE_URL, MODEL, status_response, turn_on, verdict


def settings_url(circle_id):
    return reverse("circle-ai-settings", args=[circle_id])


def connection_test_url(circle_id):
    return reverse("circle-ai-settings-test", args=[circle_id])


def scan_url(circle_id):
    return reverse("circle-milestone-scan", args=[circle_id])


def as_user(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


ENABLE = {"enabled": True, "acknowledge_data_sharing": True}


@pytest.fixture
def delay():
    with patch("mysite.ai.views.scan_milestones.delay") as mocked:
        yield mocked


@pytest.mark.django_db
class TestAccess:
    def test_jwt_only(self):
        for view in (CircleAiSettingsView, CircleAiSettingsTestView, CircleMilestoneScanView):
            assert view.authentication_classes == [JWTAuthentication]

    def test_requires_authentication(self, api_client, circle, ai_on):
        assert api_client.get(settings_url(circle.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.put(settings_url(circle.id), ENABLE).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(connection_test_url(circle.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(scan_url(circle.id)).status_code == status.HTTP_401_UNAUTHORIZED

    def test_api_tokens_are_refused(self, settings, circle, admin, ai_on, delay):
        settings.AGENT_API_ENABLED = True
        _, plaintext = create_token(circle, admin, can_suggest=True)
        agent = bearer_client(plaintext)
        turn_on(circle, admin)
        keep = make_keep(circle, admin)
        suggestion = MilestoneSuggestion.objects.create(circle=circle, keep=keep, status="pending", source="ai")

        responses = [
            agent.get(settings_url(circle.id)),
            agent.put(settings_url(circle.id), {"enabled": False}, format="json"),
            agent.post(connection_test_url(circle.id)),
            agent.post(scan_url(circle.id)),
            agent.get(reverse("circle-milestone-suggestion-list", args=[circle.id])),
            agent.post(reverse("circle-milestone-suggestion-approve", args=[circle.id, suggestion.id])),
            agent.post(reverse("circle-milestone-suggestion-dismiss", args=[circle.id, suggestion.id])),
        ]

        assert [response.status_code for response in responses] == [status.HTTP_401_UNAUTHORIZED] * 7
        assert CircleAiSettings.objects.get(circle=circle).enabled is True
        delay.assert_not_called()

    @pytest.mark.parametrize("ai_configured", [True, False])
    def test_non_member_404_member_403(self, api_client, circle, member, outsider, settings, ai_configured, delay):
        if ai_configured:
            settings.AI_BASE_URL, settings.AI_MODEL = BASE_URL, MODEL
        calls = (
            lambda client: client.get(settings_url(circle.id)),
            lambda client: client.put(settings_url(circle.id), ENABLE, format="json"),
            lambda client: client.post(connection_test_url(circle.id)),
            lambda client: client.post(scan_url(circle.id)),
        )

        for call in calls:
            assert call(as_user(api_client, outsider)).status_code == status.HTTP_404_NOT_FOUND
            assert call(as_user(api_client, member)).status_code == status.HTTP_403_FORBIDDEN
        assert not CircleAiSettings.objects.exists()
        delay.assert_not_called()

    def test_superuser_is_not_an_admin_here(self, api_client, circle, ai_on, django_user_model):
        superuser = django_user_model.objects.create_superuser(email="root@example.com", password="Passw0rd!")

        response = as_user(api_client, superuser).get(settings_url(circle.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestUnavailable:
    """While the operator hasn't set AI up (the test default)."""

    def test_get_says_unavailable_and_nothing_else(self, api_client, circle, admin):
        response = as_user(api_client, admin).get(settings_url(circle.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"available": False}

    def test_everything_else_is_404(self, api_client, circle, admin, delay):
        turn_on(circle, admin)
        client = as_user(api_client, admin)

        assert client.put(settings_url(circle.id), ENABLE, format="json").status_code == status.HTTP_404_NOT_FOUND
        assert client.post(connection_test_url(circle.id)).status_code == status.HTTP_404_NOT_FOUND
        assert client.post(scan_url(circle.id)).status_code == status.HTTP_404_NOT_FOUND
        delay.assert_not_called()

    def test_invalid_operator_config_counts_as_unavailable(self, api_client, circle, admin, settings):
        settings.AI_BASE_URL, settings.AI_MODEL, settings.AI_API_KEY = "http://ai.test/v1", MODEL, "sk-key"

        response = as_user(api_client, admin).get(settings_url(circle.id))

        assert response.json() == {"available": False}


@pytest.mark.django_db
class TestSettings:
    def test_defaults(self, api_client, circle, admin, ai_on):
        response = as_user(api_client, admin).get(settings_url(circle.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "available": True,
            "enabled": False,
            "acknowledged_at": None,
            "last_run_at": None,
            "last_success_at": None,
            "last_error": "",
            "pending_count": 0,
        }
        assert not CircleAiSettings.objects.exists()  # reading makes no row

    def test_never_returns_provider_details(self, api_client, circle, admin, ai_on):
        ai_on.AI_BASE_URL = "https://api.example.com/v1"
        ai_on.AI_API_KEY = "sk-secret-value"
        client = as_user(api_client, admin)

        bodies = [
            client.get(settings_url(circle.id)).content.decode(),
            client.put(settings_url(circle.id), ENABLE, format="json").content.decode(),
        ]

        for body in bodies:
            for secret in ("api.example.com", "sk-secret-value", MODEL, "base_url", "model"):
                assert secret not in body

    def test_enabling_needs_the_acknowledgement(self, api_client, circle, admin, ai_on):
        client = as_user(api_client, admin)

        for body in ({"enabled": True}, {"enabled": True, "acknowledge_data_sharing": False}):
            response = client.put(settings_url(circle.id), body, format="json")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json()["error"] == "ai.acknowledgement_required"
        assert not CircleAiSettings.objects.filter(enabled=True).exists()

    def test_enable_records_who_acknowledged(self, api_client, circle, admin, ai_on, caplog):
        with captured_logs(caplog, "mysite.audit"):
            response = as_user(api_client, admin).put(settings_url(circle.id), ENABLE, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["enabled"] is True
        assert response.json()["acknowledged_at"]
        ai_settings = CircleAiSettings.objects.get(circle=circle)
        assert ai_settings.enabled is True
        assert ai_settings.acknowledged_by == admin
        assert ai_settings.updated_by == admin
        assert audit_actions(caplog) == ["circle.ai_settings.update"]
        record = next(record for record in caplog.records if record.name == "mysite.audit")
        assert record.extra["metadata"] == {"fields": ["enabled"]}
        assert record.extra["actor_id"] == str(admin.pk)

    def test_turning_off_needs_no_acknowledgement(self, api_client, circle, admin, ai_on):
        turn_on(circle, admin)

        response = as_user(api_client, admin).put(settings_url(circle.id), {"enabled": False}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert CircleAiSettings.objects.get(circle=circle).enabled is False

    def test_no_change_is_not_audited(self, api_client, circle, admin, ai_on, caplog):
        turn_on(circle, admin)

        with captured_logs(caplog, "mysite.audit"):
            response = as_user(api_client, admin).put(settings_url(circle.id), {"enabled": True}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert audit_actions(caplog) == []

    @pytest.mark.parametrize(
        "extra", [{"base_url": "http://evil.test/v1"}, {"model": "other"}, {"api_key": "sk-x"}, {"url": "x"}]
    )
    def test_provider_fields_are_refused(self, api_client, circle, admin, ai_on, extra):
        response = as_user(api_client, admin).put(settings_url(circle.id), {**ENABLE, **extra}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CircleAiSettings.objects.exists()

    def test_pending_count(self, api_client, circle, admin, ai_on):
        for status_value in ("pending", "pending", "dismissed", "not_milestone"):
            MilestoneSuggestion.objects.create(
                circle=circle, keep=make_keep(circle, admin), status=status_value, source="ai"
            )

        response = as_user(api_client, admin).get(settings_url(circle.id))

        assert response.json()["pending_count"] == 2

    def test_co_admin_can_change_it(self, api_client, circle, member, ai_on):
        member.circle_memberships.filter(circle=circle).update(role=UserRole.CIRCLE_ADMIN)

        response = as_user(api_client, member).put(settings_url(circle.id), ENABLE, format="json")

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestConnectionTest:
    def test_ok_sends_only_the_synthetic_post(self, api_client, circle, admin, ai_on, provider, caplog):
        make_keep(circle, admin, title="A real family caption")
        provider.return_value = verdict(True)

        with captured_logs(caplog, "mysite.audit"):
            response = as_user(api_client, admin).post(connection_test_url(circle.id))

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["ok"] is True
        assert body["code"] == "ok"
        assert isinstance(body["latency_ms"], int)
        provider.assert_called_once()
        sent = provider.call_args.kwargs["json"]["messages"][-1]["content"]
        assert prompts.TEST_POST[1] in sent
        assert "A real family caption" not in str(provider.call_args)
        assert audit_actions(caplog) == ["circle.ai_settings.test"]
        assert CircleAiSettings.objects.count() == 0  # testing doesn't turn anything on

    @pytest.mark.parametrize(
        ("answer", "code"),
        [
            (status_response(401), "auth_failed"),
            (status_response(404), "model_missing"),
            (status_response(302), "http_error"),
            (verdict(is_milestone="yes"), "bad_response"),
        ],
    )
    def test_failures_are_fixed_codes(self, api_client, circle, admin, ai_on, provider, answer, code):
        provider.return_value = answer

        response = as_user(api_client, admin).post(connection_test_url(circle.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ok"] is False
        assert response.json()["code"] == code

    def test_rate_limited(self, api_client, circle, admin, ai_on, provider, settings):
        settings.RATELIMIT_ENABLE = True
        provider.return_value = verdict(True)
        client = as_user(api_client, admin)

        codes = [client.post(connection_test_url(circle.id)).status_code for _ in range(11)]

        assert codes == [status.HTTP_200_OK] * 10 + [status.HTTP_429_TOO_MANY_REQUESTS]
        assert provider.call_count == 10


@pytest.mark.django_db
class TestScanNow:
    def test_queues_a_scan_of_this_circle(self, api_client, circle, admin, ai_on, delay):
        turn_on(circle, admin)

        response = as_user(api_client, admin).post(scan_url(circle.id))

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"queued": True}
        delay.assert_called_once_with(circle_id=circle.id)

    def test_circle_must_have_ai_on(self, api_client, circle, admin, ai_on, delay):
        response = as_user(api_client, admin).post(scan_url(circle.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == "ai.not_enabled"
        delay.assert_not_called()

    def test_running_scan_gives_409(self, api_client, circle, admin, ai_on, delay):
        turn_on(circle, admin)

        with scan.scan_lock():
            response = as_user(api_client, admin).post(scan_url(circle.id))

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error"] == "ai.scan_running"
        delay.assert_not_called()

    def test_rate_limited(self, api_client, circle, admin, ai_on, delay, settings):
        settings.RATELIMIT_ENABLE = True
        turn_on(circle, admin)
        client = as_user(api_client, admin)

        codes = [client.post(scan_url(circle.id)).status_code for _ in range(4)]

        assert codes == [status.HTTP_202_ACCEPTED] * 3 + [status.HTTP_429_TOO_MANY_REQUESTS]
        assert delay.call_count == 3

    def test_eager_task_runs_the_scan(self, api_client, circle, admin, ai_on, provider):
        # Without mocking delay: the test settings run Celery tasks eagerly.
        turn_on(circle, admin)
        make_keep(circle, admin, title="She took her first steps")
        provider.return_value = verdict(True)

        response = as_user(api_client, admin).post(scan_url(circle.id))

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert MilestoneSuggestion.objects.get(circle=circle).status == "auto_added"
        assert cache.get(scan.LOCK_KEY) is None
