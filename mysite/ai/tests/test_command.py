"""The scan_milestones management command."""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from mysite.ai import scan
from mysite.ai.models import CircleAiSettings
from mysite.albums.models import MilestoneSuggestion

from .helpers import link_milestones_album, turn_on, verdict
from .test_scan import post

Status = MilestoneSuggestion.Status


def run(*args):
    out = StringIO()
    call_command("scan_milestones", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestScanMilestonesCommand:
    def test_dry_run_writes_nothing(self, circle, admin, ai_on, provider):
        keep = post(circle, admin, "First steps", "SECRET-CAPTION she walked")
        provider.return_value = verdict(True, label="First steps")

        output = run("--circle", circle.slug, "--dry-run")

        assert f"{keep.id}  milestone  First steps" in output
        assert "Dry run: 1 calls, 1 milestones" in output
        assert "SECRET-CAPTION" not in output
        assert not MilestoneSuggestion.objects.exists()
        assert not CircleAiSettings.objects.exists()  # works with AI off for the circle

    def test_limit_and_circle_id(self, circle, admin, ai_on, provider):
        for day in range(3):
            post(circle, admin, f"post {day}", days=day)
        provider.return_value = verdict(False)

        output = run("--circle", str(circle.id), "--dry-run", "--limit", "2")

        assert provider.call_count == 2
        assert "2 calls" in output

    def test_real_run_writes_and_records(self, circle, admin, ai_on, provider):
        ai_settings = turn_on(circle, admin)
        keep = post(circle, admin, "First steps")
        provider.return_value = verdict(True)

        run("--circle", circle.slug)

        assert MilestoneSuggestion.objects.get(keep=keep).status == Status.AUTO_ADDED
        ai_settings.refresh_from_db()
        assert ai_settings.last_success_at is not None

    def test_real_run_needs_ai_on_for_the_circle(self, circle, admin, ai_on, provider):
        post(circle, admin, "First steps")

        with pytest.raises(CommandError, match="AI is off"):
            run("--circle", circle.slug)
        provider.assert_not_called()

    def test_include_album_scores_album_posts(self, circle, admin, ai_on, provider):
        in_album = post(circle, admin, "First steps")
        link_milestones_album(circle, admin, in_album)
        provider.return_value = verdict(True)

        output = run("--circle", circle.slug, "--dry-run", "--include-album")

        assert str(in_album.id) in output
        with pytest.raises(CommandError, match="--dry-run"):
            run("--circle", circle.slug, "--include-album")

    def test_rescan_deletes_not_milestone_rows(self, circle, admin, ai_on, provider):
        turn_on(circle, admin)
        scanned = post(circle, admin, "First steps", days=1)
        MilestoneSuggestion.objects.create(circle=circle, keep=scanned, status=Status.NOT_MILESTONE, source="ai")
        dismissed = post(circle, admin, "Park", days=2)
        MilestoneSuggestion.objects.create(circle=circle, keep=dismissed, status=Status.DISMISSED, source="ai")
        provider.return_value = verdict(True)

        run("--circle", circle.slug, "--rescan")

        assert MilestoneSuggestion.objects.get(keep=scanned).status == Status.AUTO_ADDED
        assert MilestoneSuggestion.objects.get(keep=dismissed).status == Status.DISMISSED

    def test_dry_run_rescan_keeps_rows(self, circle, admin, ai_on, provider):
        scanned = post(circle, admin, "First steps")
        MilestoneSuggestion.objects.create(circle=circle, keep=scanned, status=Status.NOT_MILESTONE, source="ai")
        provider.return_value = verdict(True)

        output = run("--circle", circle.slug, "--dry-run", "--rescan")

        assert str(scanned.id) in output
        assert MilestoneSuggestion.objects.get(keep=scanned).status == Status.NOT_MILESTONE

    def test_errors(self, circle, admin, settings, provider):
        with pytest.raises(CommandError, match="not configured"):
            run("--circle", circle.slug, "--dry-run")
        settings.AI_BASE_URL, settings.AI_MODEL = "http://ai.test/v1", "m"
        with pytest.raises(CommandError, match="No circle"):
            run("--circle", "nope", "--dry-run")
        with pytest.raises(CommandError, match="--limit"):
            run("--circle", circle.slug, "--dry-run", "--limit", "0")
        with scan.scan_lock(), pytest.raises(CommandError, match="running"):
            run("--circle", circle.slug, "--dry-run")
        provider.assert_not_called()
