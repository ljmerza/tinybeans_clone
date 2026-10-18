"""The milestone scan gauges on /metrics: only when AI is configured, one series per circle with AI on."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from mysite import metrics
from mysite.ai.models import CircleAiSettings
from mysite.albums.models import MilestoneSuggestion
from mysite.albums.tests.helpers import make_keep

from .helpers import turn_on


@pytest.mark.django_db
class TestMilestoneScanGauges:
    def test_no_check_while_ai_is_not_configured(self, circle, admin):
        turn_on(circle, admin)

        assert "milestone_scans" not in metrics.build_checks()

    def test_check_registered_when_ai_is_configured(self, ai_on):
        assert "milestone_scans" in metrics.build_checks()

    def test_gauges(self, circle, other_circle, admin, outsider, ai_on):
        success = timezone.now() - timedelta(hours=3)
        acknowledged = timezone.now() - timedelta(days=1)
        ai_settings = turn_on(circle, admin)
        ai_settings.last_success_at = success
        ai_settings.save()
        CircleAiSettings.objects.create(circle=other_circle, enabled=True, acknowledged_at=acknowledged)
        for status_value in ("pending", "pending", "dismissed"):
            MilestoneSuggestion.objects.create(
                circle=circle, keep=make_keep(circle, admin), status=status_value, source="ai"
            )

        samples = metrics.check_milestone_scans()
        body = metrics.render(samples)

        assert (
            "circles_milestone_scan_last_success_timestamp_seconds",
            {"circle_id": str(circle.id)},
            success.timestamp(),
        ) in samples
        assert (
            "circles_milestone_scan_last_success_timestamp_seconds",
            {"circle_id": str(other_circle.id)},
            acknowledged.timestamp(),  # before the first success
        ) in samples
        assert ("circles_milestone_suggestions_pending", {"circle_id": str(circle.id)}, 2) in samples
        assert ("circles_milestone_suggestions_pending", {"circle_id": str(other_circle.id)}, 0) in samples
        assert "# TYPE circles_milestone_suggestions_pending gauge" in body

    def test_turning_ai_back_on_restarts_the_clock(self, circle, admin, ai_on):
        old_success = timezone.now() - timedelta(days=30)
        turned_back_on = timezone.now() - timedelta(hours=1)
        CircleAiSettings.objects.create(
            circle=circle, enabled=True, last_success_at=old_success, acknowledged_at=turned_back_on
        )

        samples = metrics.check_milestone_scans()

        assert (
            "circles_milestone_scan_last_success_timestamp_seconds",
            {"circle_id": str(circle.id)},
            turned_back_on.timestamp(),
        ) in samples

    def test_circles_with_ai_off_have_no_series(self, circle, admin, ai_on):
        CircleAiSettings.objects.create(circle=circle, enabled=False)

        assert metrics.check_milestone_scans() == []

    def test_check_thread_closes_its_connection(self, ai_on):
        with patch.object(metrics.connections, "close_all") as close_all:
            assert metrics.build_checks()["milestone_scans"]() == []

        close_all.assert_called_once()

    def test_failing_check_reports_down(self, ai_on):
        with (
            patch.object(metrics.connections, "close_all") as close_all,
            patch.object(metrics, "check_milestone_scans", side_effect=RuntimeError("db down")),
        ):
            checks = {"milestone_scans": metrics._closing_db_connections(metrics.check_milestone_scans)}
            samples = metrics.run_checks(checks)

        assert ("circles_dependency_up", {"dependency": "milestone_scans"}, 0) in samples
        close_all.assert_called_once()
