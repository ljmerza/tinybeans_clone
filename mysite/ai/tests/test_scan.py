"""The milestone scan: candidates, verdicts, caps and stops, the lock, the task and its schedule."""

from datetime import timedelta
from unittest.mock import patch

import pytest
import requests
from celery.exceptions import Retry, SoftTimeLimitExceeded
from celery.schedules import crontab
from django.conf import settings as django_settings
from django.core.cache import cache
from django.utils import timezone

from mysite.agent_api.tests.helpers import audit_actions, captured_logs
from mysite.ai import scan
from mysite.ai.models import CircleAiSettings
from mysite.ai.providers import provider_config
from mysite.albums import milestones
from mysite.albums.models import AlbumKeep, MilestoneSuggestion
from mysite.albums.tasks import scan_milestones
from mysite.albums.tests.helpers import BASE_TIME, make_album, make_keep
from mysite.keeps.models import KeepComment

from .helpers import MODEL, chat_response, link_milestones_album, sent_posts, status_response, turn_on, verdict

Status = MilestoneSuggestion.Status


def post(circle, user, title, caption="", *, days=0, media=(("photo", True),)):
    """A post ``days`` after BASE_TIME, so a bigger ``days`` is newer."""
    keep = make_keep(circle, user, BASE_TIME + timedelta(days=days), media=media, title=title)
    keep.description = caption
    keep.save(update_fields=["description"])
    return keep


def config():
    return provider_config()


@pytest.mark.django_db
class TestCandidates:
    def test_exclusions_and_order(self, circle, other_circle, admin, outsider):
        older = post(circle, admin, "older", days=1)
        newer = post(circle, admin, "newer", days=2)
        text_post = post(circle, admin, "text only", days=3, media=())
        post(circle, admin, "video still processing", days=4, media=(("video", False),))
        ready_video = post(circle, admin, "video ready", days=5, media=(("video", True),))
        scanned = post(circle, admin, "scanned", days=6)
        MilestoneSuggestion.objects.create(circle=circle, keep=scanned, status=Status.NOT_MILESTONE, source="ai")
        dismissed = post(circle, admin, "dismissed", days=7)
        MilestoneSuggestion.objects.create(circle=circle, keep=dismissed, status=Status.DISMISSED, source="agent")
        in_album = post(circle, admin, "in album", days=8)
        link_milestones_album(circle, admin, in_album)
        in_other_album = post(circle, admin, "in a different album", days=9)
        make_album(circle, admin, keeps=[in_other_album])
        post(other_circle, outsider, "other circle", days=10)

        candidates = list(milestones.scan_candidates(circle.id))

        assert candidates == [in_other_album, ready_video, text_post, newer, older]

    def test_command_options(self, circle, admin):
        scanned = post(circle, admin, "scanned", days=1)
        MilestoneSuggestion.objects.create(circle=circle, keep=scanned, status=Status.NOT_MILESTONE, source="ai")
        in_album = post(circle, admin, "in album", days=2)
        link_milestones_album(circle, admin, in_album)

        assert list(milestones.scan_candidates(circle.id, include_album=True)) == [in_album]
        assert list(milestones.scan_candidates(circle.id, include_not_milestone=True)) == [scanned]


@pytest.mark.django_db
class TestScanCircle:
    @pytest.fixture(autouse=True)
    def _turned_on(self, circle, admin):
        turn_on(circle, admin)

    def test_birthday_and_empty_posts_are_skipped_without_a_call(self, circle, admin, ai_on, provider):
        post(circle, admin, "Happy birthday!", days=1)
        post(circle, admin, "", "Happy 1 month birthday little man", days=2)
        post(circle, admin, "", "her half birthday", days=3)
        post(circle, admin, "  ", "  ", days=4)
        six_months = post(circle, admin, "Turned 6 months today", days=5)
        provider.return_value = verdict(False)

        summary = scan.scan_circle(circle.id, config())

        assert summary.skipped_birthday == 3
        assert summary.skipped_empty == 1
        assert summary.calls == 1
        assert "Turned 6 months today" in sent_posts(provider)[0]
        assert list(MilestoneSuggestion.objects.values_list("keep_id", flat=True)) == [six_months.id]

    def test_milestone_goes_into_the_album_with_review_off(self, circle, admin, ai_on, provider):
        keep = post(circle, admin, "First steps!", "She walked to the couch")
        provider.return_value = verdict(True, label="First steps", reason="She walked.")

        summary = scan.scan_circle(circle.id, config())

        suggestion = MilestoneSuggestion.objects.get(keep=keep)
        assert suggestion.status == Status.AUTO_ADDED
        assert suggestion.source == MilestoneSuggestion.Source.AI
        assert (suggestion.label, suggestion.reason, suggestion.model_name) == ("First steps", "She walked.", MODEL)
        assert AlbumKeep.objects.filter(keep=keep, album__milestone_album__circle=circle).exists()
        assert summary.proposed == 1

    def test_milestone_waits_for_review_with_review_on(self, circle, admin, ai_on, provider):
        circle.review_ai_milestones = True
        circle.save()
        keep = post(circle, admin, "First tooth")
        provider.return_value = verdict(True)

        scan.scan_circle(circle.id, config())

        assert MilestoneSuggestion.objects.get(keep=keep).status == Status.PENDING
        assert not AlbumKeep.objects.filter(keep=keep).exists()

    def test_no_and_invalid_answers_mark_the_post_scanned(self, circle, admin, ai_on, provider):
        no = post(circle, admin, "Park day", days=2)
        invalid = post(circle, admin, "Something", days=1)
        provider.side_effect = [verdict(False, label="x", reason="Routine."), chat_response("not json at all")]

        summary = scan.scan_circle(circle.id, config())

        rows = {row.keep_id: row for row in MilestoneSuggestion.objects.all()}
        for keep in (no, invalid):
            assert rows[keep.id].status == Status.NOT_MILESTONE
            assert rows[keep.id].reason == ""
            assert rows[keep.id].label == ""
            assert rows[keep.id].model_name == MODEL
        assert (summary.not_milestone, summary.invalid) == (1, 1)
        assert list(milestones.scan_candidates(circle.id)) == []

    def test_failed_calls_write_nothing_so_the_post_is_retried(self, circle, admin, ai_on, provider):
        keep = post(circle, admin, "First steps")
        provider.side_effect = requests.ConnectionError("down")

        summary = scan.scan_circle(circle.id, config())

        assert summary.failed == 1
        assert not MilestoneSuggestion.objects.exists()
        assert list(milestones.scan_candidates(circle.id)) == [keep]

    def test_newest_first_up_to_the_call_cap(self, circle, admin, ai_on, provider):
        ai_on.AI_MAX_CALLS_PER_RUN = 2
        for day in range(1, 5):
            post(circle, admin, f"post {day}", days=day)
        provider.return_value = verdict(False)

        summary = scan.scan_circle(circle.id, config())

        assert summary.calls == 2
        assert summary.stopped == ""
        sent = sent_posts(provider)
        assert "post 4" in sent[0]
        assert "post 3" in sent[1]

    def test_pending_cap_stops_the_run(self, circle, admin, ai_on, provider, settings):
        settings.MILESTONE_MAX_PENDING = 2
        circle.review_ai_milestones = True
        circle.save()
        for day in range(1, 5):
            post(circle, admin, f"post {day}", days=day)
        provider.return_value = verdict(True)

        summary = scan.scan_circle(circle.id, config())

        assert summary.calls == 2
        assert summary.stopped == scan.PENDING_CAP
        assert MilestoneSuggestion.objects.filter(status=Status.PENDING).count() == 2

    def test_pending_cap_does_not_apply_with_review_off(self, circle, admin, ai_on, provider, settings):
        settings.MILESTONE_MAX_PENDING = 1
        MilestoneSuggestion.objects.create(
            circle=circle, keep=post(circle, admin, "old pick", days=0), status=Status.PENDING, source="ai"
        )
        for day in range(1, 3):
            post(circle, admin, f"post {day}", days=day)
        provider.return_value = verdict(True)

        summary = scan.scan_circle(circle.id, config())

        assert summary.stopped == ""
        assert MilestoneSuggestion.objects.filter(status=Status.AUTO_ADDED).count() == 2

    @pytest.mark.parametrize("code_status", [401, 404, 503])
    def test_some_errors_abort_at_once(self, circle, admin, ai_on, provider, code_status):
        for day in range(1, 4):
            post(circle, admin, f"post {day}", days=day)
        provider.return_value = status_response(code_status)

        summary = scan.scan_circle(circle.id, config())

        assert summary.calls == 1
        assert summary.stopped in {"auth_failed", "model_missing", "provider_unavailable"}

    def test_three_failures_in_a_row_abort(self, circle, admin, ai_on, provider):
        for day in range(1, 8):
            post(circle, admin, f"post {day}", days=day)
        timeout = requests.ReadTimeout("slow")
        provider.side_effect = [timeout, verdict(False), timeout, status_response(500), timeout, verdict(False)]

        summary = scan.scan_circle(circle.id, config())

        assert summary.calls == 5
        assert summary.stopped == "timeout"
        assert summary.failed == 4
        assert MilestoneSuggestion.objects.count() == 1

    def test_turning_ai_off_stops_the_run_before_the_next_call(self, circle, admin, ai_on, provider):
        for day in range(1, 4):
            post(circle, admin, f"post {day}", days=day)

        def answer_then_turn_off(*args, **kwargs):
            CircleAiSettings.objects.filter(circle=circle).update(enabled=False)
            return verdict(False)

        provider.side_effect = answer_then_turn_off

        summary = scan.scan_circle(circle.id, config())

        assert provider.call_count == 1
        assert summary.calls == 1
        assert summary.stopped == scan.DISABLED
        assert summary.succeeded is False
        assert MilestoneSuggestion.objects.count() == 1  # the answer already given is kept

    def test_dry_run_does_not_need_ai_on(self, circle, admin, ai_on, provider):
        CircleAiSettings.objects.filter(circle=circle).update(enabled=False)
        post(circle, admin, "First steps")
        provider.return_value = verdict(True)

        summary = scan.scan_circle(circle.id, config(), dry_run=True)

        assert (summary.calls, summary.stopped) == (1, "")

    def test_dry_run_writes_nothing(self, circle, admin, ai_on, provider):
        post(circle, admin, "First steps", days=1)
        post(circle, admin, "Park", days=2)
        provider.side_effect = [verdict(False), verdict(True)]
        seen = []

        summary = scan.scan_circle(circle.id, config(), dry_run=True, on_result=lambda *args: seen.append(args))

        assert (summary.calls, summary.proposed, summary.not_milestone) == (2, 1, 1)
        assert len(seen) == 2
        assert not MilestoneSuggestion.objects.exists()
        assert not AlbumKeep.objects.exists()

    def test_prompt_has_only_title_and_caption(self, circle, admin, member, ai_on, provider):
        admin.first_name = "Adalyn"
        admin.save()
        keep = post(circle, admin, "Big day", "First steps! Video: https://cdn.example/clip.mp4")
        KeepComment.objects.create(keep=keep, user=member, comment="COMMENT-TEXT so proud of her")
        provider.return_value = verdict(True)

        scan.scan_circle(circle.id, config())

        payload = str(provider.call_args.kwargs["json"])
        assert "Big day" in payload
        for leaked in (
            "COMMENT-TEXT",
            "Adalyn",
            admin.email,
            member.email,
            str(keep.id),
            "cdn.example",
            "original/",
            "gallery/",
            "AI Family",
            "2026",
        ):
            assert leaked not in payload


@pytest.mark.django_db
class TestRunScan:
    def test_only_circles_with_ai_on(self, circle, other_circle, admin, outsider, ai_on, provider):
        turn_on(circle, admin)
        CircleAiSettings.objects.create(circle=other_circle, enabled=False)
        post(circle, admin, "mine")
        post(other_circle, outsider, "theirs")
        provider.return_value = verdict(False)

        results = scan.run_scan()

        assert list(results) == [circle.id]
        assert provider.call_count == 1
        assert not MilestoneSuggestion.objects.filter(circle=other_circle).exists()

    def test_one_circle(self, circle, other_circle, admin, outsider, ai_on, provider):
        turn_on(circle, admin)
        turn_on(other_circle, outsider)
        provider.return_value = verdict(False)

        assert list(scan.run_scan(other_circle.id)) == [other_circle.id]

    def test_skipped_when_ai_is_not_configured(self, circle, admin, provider):
        turn_on(circle, admin)
        post(circle, admin, "x")

        assert scan.run_scan() == {"skipped": "ai_disabled"}
        provider.assert_not_called()

    def test_skipped_while_another_scan_runs(self, circle, admin, ai_on, provider):
        turn_on(circle, admin)
        post(circle, admin, "x")

        with scan.scan_lock():
            assert scan.run_scan() == {"skipped": "running"}
            with pytest.raises(scan.ScanRunning), scan.scan_lock():
                pass
        provider.assert_not_called()
        assert cache.get(scan.LOCK_KEY) is None

    def test_success_is_recorded(self, circle, admin, ai_on, provider):
        ai_settings = turn_on(circle, admin)
        post(circle, admin, "x")
        provider.return_value = verdict(False)

        scan.run_scan()

        ai_settings.refresh_from_db()
        assert ai_settings.last_run_at is not None
        assert ai_settings.last_success_at == ai_settings.last_run_at
        assert ai_settings.last_error == ""
        assert cache.get(scan.LOCK_KEY) is None

    def test_failure_is_recorded(self, circle, admin, ai_on, provider):
        ai_settings = turn_on(circle, admin)
        post(circle, admin, "x")
        provider.return_value = status_response(401)

        scan.run_scan()

        ai_settings.refresh_from_db()
        assert ai_settings.last_run_at is not None
        assert ai_settings.last_success_at is None
        assert ai_settings.last_error == "auth_failed"

    def test_soft_time_limit_keeps_what_was_written(self, circle, other_circle, admin, outsider, ai_on, provider):
        ai_settings = turn_on(circle, admin)
        turn_on(other_circle, outsider)
        first = post(circle, admin, "first", days=2)
        post(circle, admin, "second", days=1)
        post(other_circle, outsider, "other")
        provider.side_effect = [verdict(False), SoftTimeLimitExceeded()]

        results = scan.run_scan()

        assert list(MilestoneSuggestion.objects.values_list("keep_id", flat=True)) == [first.id]
        assert results[circle.id]["stopped"] == scan.TIME_LIMIT
        assert other_circle.id not in results  # stops there
        ai_settings.refresh_from_db()
        assert ai_settings.last_error == scan.TIME_LIMIT
        assert ai_settings.last_success_at is None
        assert cache.get(scan.LOCK_KEY) is None

    def test_turned_off_mid_run_skips_later_circles_and_keeps_last_success(
        self, circle, other_circle, admin, outsider, ai_on, provider, caplog
    ):
        earlier = timezone.now() - timedelta(days=3)
        ai_settings = turn_on(circle, admin)
        CircleAiSettings.objects.filter(circle=circle).update(last_success_at=earlier)
        turn_on(other_circle, outsider)
        post(circle, admin, "first", days=2)
        post(circle, admin, "second", days=1)
        post(other_circle, outsider, "other")

        def answer_then_turn_both_off(*args, **kwargs):
            CircleAiSettings.objects.update(enabled=False)
            return verdict(False)

        provider.side_effect = answer_then_turn_both_off

        with captured_logs(caplog, "mysite.audit"):
            results = scan.run_scan()

        assert provider.call_count == 1
        assert results[circle.id]["stopped"] == scan.DISABLED
        assert other_circle.id not in results
        assert not MilestoneSuggestion.objects.filter(circle=other_circle).exists()
        ai_settings.refresh_from_db()
        assert ai_settings.last_success_at == earlier
        assert ai_settings.last_error == scan.DISABLED
        run = next(record for record in caplog.records if record.extra.get("action") == "milestone_scan.run")
        assert run.extra["status"] == "success"  # not the provider's fault

    def test_run_is_audited_with_counts_only(self, circle, admin, ai_on, provider, caplog):
        turn_on(circle, admin)
        secret_caption = "CAPTION-SECRET she walked to Grandma"
        secret_reason = "REASON-SECRET walked"
        post(circle, admin, "First steps", secret_caption, days=2)
        post(circle, admin, "Park", "PARK-SECRET", days=1)
        provider.side_effect = [verdict(True, reason=secret_reason), chat_response("RAW-ANSWER-SECRET")]

        with captured_logs(caplog, "mysite.audit", "django.request", "celery", "mysite.ai.scan"):
            scan.run_scan()

        assert audit_actions(caplog) == ["milestone_suggestion.propose", "milestone_scan.run"]
        run = next(record for record in caplog.records if record.extra.get("action") == "milestone_scan.run")
        metadata = run.extra["metadata"]
        assert metadata["calls"] == 2
        assert metadata["proposed"] == 1
        assert metadata["invalid"] == 1
        assert metadata["trigger"] == "beat"
        logged = " ".join(f"{record.getMessage()} {getattr(record, 'extra', '')}" for record in caplog.records)
        for secret in (secret_caption, secret_reason, "PARK-SECRET", "RAW-ANSWER-SECRET", "First steps"):
            assert secret not in logged


@pytest.mark.django_db
class TestTask:
    def test_runs_the_scan(self, circle, admin, ai_on, provider):
        turn_on(circle, admin)
        keep = post(circle, admin, "First steps")
        provider.return_value = verdict(True)

        result = scan_milestones.apply(kwargs={"circle_id": circle.id}).get()

        assert result[circle.id]["proposed"] == 1
        assert MilestoneSuggestion.objects.get(keep=keep).status == Status.AUTO_ADDED

    def test_options(self):
        assert scan_milestones.soft_time_limit == 3000
        assert scan_milestones.time_limit == 3300
        assert scan_milestones.time_limit < scan.LOCK_TIMEOUT_SECONDS
        assert not getattr(scan_milestones, "autoretry_for", ())
        # Retrying a nightly run blocked by the lock outlasts any scan holding it.
        assert scan_milestones.max_retries * scan_milestones.default_retry_delay > scan_milestones.time_limit

    def test_nightly_run_retries_while_another_scan_holds_the_lock(self, circle, admin, ai_on, provider):
        turn_on(circle, admin)
        post(circle, admin, "x")

        with (
            scan.scan_lock(),
            patch.object(scan_milestones, "retry", side_effect=Retry()) as retry,
            pytest.raises(Retry),
        ):
            scan_milestones()
        retry.assert_called_once_with()
        provider.assert_not_called()

    def test_nightly_run_gives_up_after_its_retries(self, circle, admin, ai_on, provider):
        turn_on(circle, admin)

        with scan.scan_lock(), patch.object(scan_milestones, "retry") as retry:
            result = scan_milestones.apply(retries=scan_milestones.max_retries).get()

        assert result == {"skipped": "running"}
        retry.assert_not_called()

    def test_scan_now_does_not_retry(self, circle, admin, ai_on, provider):
        turn_on(circle, admin)

        with scan.scan_lock(), patch.object(scan_milestones, "retry") as retry:
            result = scan_milestones.apply(kwargs={"circle_id": circle.id}).get()

        assert result == {"skipped": "running"}
        retry.assert_not_called()

    def test_queue_route_and_schedule(self):
        assert "ai" in {queue.name for queue in django_settings.CELERY_TASK_QUEUES}
        assert django_settings.CELERY_TASK_ROUTES["mysite.albums.tasks.scan_milestones"] == {"queue": "ai"}
        entry = django_settings.CELERY_BEAT_SCHEDULE["scan-milestones"]
        assert entry["task"] == "mysite.albums.tasks.scan_milestones"
        assert entry["schedule"] == crontab(hour=1, minute=0)


def test_every_last_error_code_fits_the_column():
    # SQLite doesn't enforce varchar lengths; Postgres would refuse a longer code.
    from mysite.ai import client

    codes = {
        client.TIMEOUT,
        client.UNREACHABLE,
        client.AUTH_FAILED,
        client.MODEL_MISSING,
        client.HTTP_ERROR,
        client.BAD_RESPONSE,
        client.PROVIDER_UNAVAILABLE,
        scan.PENDING_CAP,
        scan.TIME_LIMIT,
        scan.DISABLED,
    }
    assert max(len(code) for code in codes) <= CircleAiSettings._meta.get_field("last_error").max_length
