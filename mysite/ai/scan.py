"""The milestone scan: each new post's caption goes to the operator's model, one post per call.

Run nightly by ``mysite.albums.tasks.scan_milestones`` (and on demand by a
circle admin, or the ``scan_milestones`` command). Circles are scanned one
after another, newest posts first, under one global lock: the local model
serves one request at a time.

Per post (each written on its own, so a stop keeps what was done):

- birthday or empty title and caption: skipped, no call and no row;
- a milestone: ``milestones.propose``, so the circle's review setting applies;
- not a milestone, or an answer that doesn't fit the schema: a
  ``not_milestone`` row, so it isn't sent again;
- a failed call: no row, so the post is tried again next run.

A circle's run stops at ``AI_MAX_CALLS_PER_RUN`` calls, when its pending
queue is full (``pending_cap``), at once on ``auth_failed``,
``model_missing`` or ``provider_unavailable``, and after 3 failed calls in a
row. Prompts, captions and model answers are never logged; the run summary
has counts only.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass

from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from mysite.albums import milestones
from mysite.albums.models import MilestoneSuggestion
from mysite.audit import AuditEvent, log_audit_event
from mysite.circles.models import Circle

from . import client, prompts
from .models import CircleAiSettings
from .providers import ProviderConfig, provider_config

logger = logging.getLogger(__name__)

LOCK_KEY = "ai:milestone-scan"
# A little longer than the task's hard time limit, so a killed worker can't hold it forever.
LOCK_TIMEOUT_SECONDS = 56 * 60

PENDING_CAP = "pending_cap"
TIME_LIMIT = "time_limit"
# Stop the circle's run at once: every further call would fail the same way.
ABORT_CODES = {client.AUTH_FAILED, client.MODEL_MISSING, client.PROVIDER_UNAVAILABLE}
# Stop after this many in a row.
STREAK_CODES = {client.TIMEOUT, client.UNREACHABLE, client.HTTP_ERROR, client.BAD_RESPONSE}
MAX_FAILURE_STREAK = 3

Status = MilestoneSuggestion.Status


class ScanRunning(Exception):  # noqa: N818 - a state, not a programming error
    """Another scan holds the lock."""


@contextmanager
def scan_lock() -> Iterator[None]:
    """Hold the global scan lock, or raise ``ScanRunning``."""
    if not cache.add(LOCK_KEY, 1, LOCK_TIMEOUT_SECONDS):
        raise ScanRunning
    try:
        yield
    finally:
        cache.delete(LOCK_KEY)


def scan_running() -> bool:
    return cache.get(LOCK_KEY) is not None


@dataclass
class ScanSummary:
    """Counts for one circle's run; what goes in ``milestone_scan.run``. No text from posts or the model."""

    calls: int = 0
    proposed: int = 0
    not_milestone: int = 0
    invalid: int = 0
    failed: int = 0
    skipped_birthday: int = 0
    skipped_empty: int = 0
    # Why the run stopped early: an ``AiError`` code, ``pending_cap`` or ``time_limit``.
    stopped: str = ""
    # The last failed call's code, if any.
    last_failure: str = ""

    @property
    def succeeded(self) -> bool:
        """The provider worked: no stop on an error, and not every call failed."""
        if self.stopped and self.stopped != PENDING_CAP:
            return False
        return self.calls == 0 or self.failed < self.calls

    @property
    def error_code(self) -> str:
        return self.stopped or self.last_failure


# Called for each post sent to the model with (keep, verdict, error code): the verdict is None
# for a failed call (code set) or an invalid answer (code empty).
ResultCallback = Callable[..., None]


def _pending_full(circle_id: int, review: bool) -> bool:
    # Only review-on picks wait in the queue; with review off they go straight into the album.
    return review and milestones.pending_suggestions(circle_id).count() >= settings.MILESTONE_MAX_PENDING


def _mark_not_milestone(keep, config: ProviderConfig) -> None:
    MilestoneSuggestion.objects.get_or_create(
        keep=keep,
        defaults={
            "circle_id": keep.circle_id,
            "status": Status.NOT_MILESTONE,
            "source": MilestoneSuggestion.Source.AI,
            "model_name": config.model[: MilestoneSuggestion._meta.get_field("model_name").max_length],
        },
    )


def scan_circle(
    circle_id: int,
    config: ProviderConfig,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    include_album: bool = False,
    include_not_milestone: bool = False,
    on_result: ResultCallback | None = None,
    summary: ScanSummary | None = None,
) -> ScanSummary:
    """Scan one circle's new posts (see the module docstring). The caller holds the lock.

    ``dry_run`` calls the model but writes nothing. ``summary`` is filled in
    as it goes, so a caller that catches a soft time limit still has the counts.
    """
    summary = summary if summary is not None else ScanSummary()
    limit = config.max_calls_per_run if limit is None else limit
    review = Circle.objects.filter(pk=circle_id).values_list("review_ai_milestones", flat=True).first() or False
    keeps = milestones.scan_candidates(
        circle_id, include_album=include_album, include_not_milestone=include_not_milestone
    ).only("id", "circle_id", "title", "description")
    streak = 0

    for keep in list(keeps):
        if milestones.mentions_birthday(f"{keep.title}\n{keep.description}"):
            summary.skipped_birthday += 1
            continue
        if not keep.title.strip() and not keep.description.strip():
            summary.skipped_empty += 1  # left for photo analysis (phase 2)
            continue
        if summary.calls >= limit:
            break
        if _pending_full(circle_id, review):
            summary.stopped = PENDING_CAP
            break

        summary.calls += 1
        verdict, code = None, ""
        try:
            verdict = client.classify_post(config, keep.title, keep.description)
        except client.AiError as exc:
            code = exc.code
        except client.InvalidOutput:
            pass

        if code:
            summary.failed += 1
            summary.last_failure = code
            streak = streak + 1 if code in STREAK_CODES else 0
            if on_result:
                on_result(keep, None, code)
            if code in ABORT_CODES or streak >= MAX_FAILURE_STREAK:
                summary.stopped = code
                break
            continue
        streak = 0
        if on_result:
            on_result(keep, verdict, "")

        if verdict is not None and verdict.is_milestone:
            summary.proposed += 1
            if dry_run:
                continue
            result = milestones.propose(
                circle_id=circle_id,
                keep=keep,
                source=MilestoneSuggestion.Source.AI,
                label=verdict.label,
                reason=verdict.reason,
                model_name=config.model,
            )
            if result.outcome == milestones.PENDING_CAP:
                # Nothing written: the post is tried again once admins have reviewed some.
                summary.proposed -= 1
                summary.stopped = PENDING_CAP
                break
        else:
            if verdict is None:
                summary.invalid += 1
            else:
                summary.not_milestone += 1
            if not dry_run:
                _mark_not_milestone(keep, config)
    return summary


def record_run(ai_settings: CircleAiSettings, summary: ScanSummary, *, trigger: str) -> None:
    """Save the run's status on the circle's settings and log ``milestone_scan.run`` (counts only)."""
    now = timezone.now()
    ai_settings.last_run_at = now
    ai_settings.last_error = summary.error_code
    fields = ["last_run_at", "last_error", "updated_at"]
    if summary.succeeded:
        ai_settings.last_success_at = now
        fields.append("last_success_at")
    ai_settings.save(update_fields=fields)
    log_audit_event(
        AuditEvent(
            action="milestone_scan.run",
            actor_type="system",
            target_type="circle",
            target_id=str(ai_settings.circle_id),
            status="success" if summary.succeeded else "failure",
            metadata={**asdict(summary), "trigger": trigger, "prompt_version": prompts.PROMPT_VERSION},
        )
    )


def run_scan(circle_id: int | None = None, *, trigger: str = "beat") -> dict:
    """Scan every circle with AI turned on (or just ``circle_id``), one at a time, under the lock.

    Returns ``{circle_id: summary dict}``, or ``{"skipped": reason}`` when AI
    is off or another scan is running. A soft time limit stops it cleanly:
    rows already written stay, and the circle being scanned records ``time_limit``.
    """
    config = provider_config()
    if config is None:
        logger.info("Milestone scan skipped: AI is not configured")
        return {"skipped": "ai_disabled"}

    enabled = CircleAiSettings.objects.filter(enabled=True).order_by("circle_id")
    if circle_id is not None:
        enabled = enabled.filter(circle_id=circle_id)

    results: dict = {}
    try:
        with scan_lock():
            for ai_settings in enabled:
                summary = ScanSummary()
                try:
                    scan_circle(ai_settings.circle_id, config, summary=summary)
                except SoftTimeLimitExceeded:
                    summary.stopped = TIME_LIMIT
                    record_run(ai_settings, summary, trigger=trigger)
                    results[ai_settings.circle_id] = asdict(summary)
                    logger.warning("Milestone scan hit its time limit in circle %s", ai_settings.circle_id)
                    break
                record_run(ai_settings, summary, trigger=trigger)
                results[ai_settings.circle_id] = asdict(summary)
    except ScanRunning:
        logger.info("Milestone scan skipped: another scan is running")
        return {"skipped": "running"}
    return results
