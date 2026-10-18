"""Django admin for in-app AI: a superuser can only switch a circle off."""

from unittest.mock import Mock

import pytest
from django.contrib.admin.sites import site
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.utils import timezone

from mysite.agent_api.tests.helpers import audit_actions, captured_logs
from mysite.ai.admin import CircleAiSettingsAdmin
from mysite.ai.models import CircleAiSettings

from .helpers import turn_on


@pytest.mark.django_db
class TestCircleAiSettingsAdmin:
    @pytest.fixture
    def model_admin(self):
        return CircleAiSettingsAdmin(CircleAiSettings, site)

    @pytest.fixture
    def request_(self, django_user_model):
        request = RequestFactory().post("/")
        request.user = django_user_model.objects.create_superuser(email="root@example.com", password="Passw0rd!")
        return request

    def test_only_enabled_is_editable(self, model_admin, request_):
        assert set(model_admin.fields) - set(model_admin.readonly_fields) == {"enabled"}
        assert model_admin.has_add_permission(request_) is False
        assert model_admin.has_delete_permission(request_) is False

    def test_turning_a_circle_off_is_audited(self, model_admin, request_, circle, admin, caplog):
        ai_settings = turn_on(circle, admin)
        form = model_admin.get_form(request_, ai_settings)(data={"enabled": False}, instance=ai_settings)
        assert form.is_valid(), form.errors

        with captured_logs(caplog, "mysite.audit"):
            model_admin.save_model(request_, form.save(commit=False), form, change=True)

        ai_settings.refresh_from_db()
        assert ai_settings.enabled is False
        assert ai_settings.updated_by == request_.user
        assert audit_actions(caplog) == ["circle.ai_settings.update"]

    def test_a_circle_that_is_off_cannot_be_turned_on(self, model_admin, request_, circle):
        ai_settings = CircleAiSettings.objects.create(circle=circle, enabled=False)

        assert "enabled" in model_admin.get_readonly_fields(request_, ai_settings)
        assert "enabled" not in model_admin.get_readonly_fields(request_, turn_on(circle))

    def test_turning_on_is_refused_even_if_the_form_allows_it(self, model_admin, request_, circle, caplog):
        ai_settings = CircleAiSettings.objects.create(circle=circle, enabled=False)
        ai_settings.enabled = True

        with captured_logs(caplog, "mysite.audit"), pytest.raises(PermissionDenied):
            model_admin.save_model(request_, ai_settings, Mock(changed_data=["enabled"]), change=True)

        ai_settings.refresh_from_db()
        assert ai_settings.enabled is False
        assert ai_settings.acknowledged_at is None
        assert audit_actions(caplog) == []

    def test_turning_off_keeps_scan_status_written_since_the_page_loaded(self, model_admin, request_, circle, admin):
        ai_settings = turn_on(circle, admin)
        form = model_admin.get_form(request_, ai_settings)(data={"enabled": False}, instance=ai_settings)
        assert form.is_valid(), form.errors
        finished = timezone.now()
        CircleAiSettings.objects.filter(circle=circle).update(
            last_run_at=finished, last_success_at=finished, last_error="pending_cap"
        )

        model_admin.save_model(request_, form.save(commit=False), form, change=True)

        ai_settings.refresh_from_db()
        assert ai_settings.enabled is False
        assert (ai_settings.last_run_at, ai_settings.last_success_at) == (finished, finished)
        assert ai_settings.last_error == "pending_cap"
