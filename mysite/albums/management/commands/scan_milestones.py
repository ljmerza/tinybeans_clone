"""Run the AI milestone scan for one circle by hand, e.g. to measure latency or check recall.

    python manage.py scan_milestones --circle family --dry-run --limit 20
    python manage.py scan_milestones --circle family --dry-run --include-album

Same rules as the nightly scan (see ``mysite.ai.scan``). Every run calls the
operator's model. ``--dry-run`` writes nothing; without it the circle must
have AI turned on. Output is post ids, verdicts and labels, never captions.
"""

from django.core.management.base import BaseCommand, CommandError

from mysite.ai import scan
from mysite.ai.models import CircleAiSettings
from mysite.ai.providers import provider_config
from mysite.albums.models import MilestoneSuggestion
from mysite.circles.models import Circle


class Command(BaseCommand):
    help = "Ask the AI model which of a circle's new posts are milestones."

    def add_arguments(self, parser):
        parser.add_argument("--circle", required=True, help="Circle id or slug")
        parser.add_argument("--limit", type=int, help="Most model calls (default AI_MAX_CALLS_PER_RUN)")
        parser.add_argument("--dry-run", action="store_true", help="Call the model but write nothing")
        parser.add_argument(
            "--include-album",
            action="store_true",
            help="Also score posts already in the Milestones album, as a recall check (needs --dry-run)",
        )
        parser.add_argument(
            "--rescan",
            action="store_true",
            help="Score posts the AI already said no to again (without --dry-run, their rows are deleted first)",
        )

    def handle(self, *args, circle, limit, dry_run, include_album, rescan, **options):
        found = Circle.objects.filter(id=int(circle)) if circle.isdigit() else Circle.objects.filter(slug=circle)
        target = found.first()
        if target is None:
            raise CommandError(f"No circle {circle!r}.")
        if limit is not None and limit < 1:
            raise CommandError("--limit must be at least 1.")
        if include_album and not dry_run:
            raise CommandError("--include-album only scores posts; use it with --dry-run.")
        config = provider_config()
        if config is None:
            raise CommandError("AI is not configured: set AI_BASE_URL and AI_MODEL (see mysite/config/settings/ai.py).")
        ai_settings = CircleAiSettings.objects.filter(circle=target).first()
        if not dry_run and not (ai_settings and ai_settings.enabled):
            raise CommandError(f"AI is off for {target}; a circle admin turns it on, or use --dry-run.")

        def report(keep, verdict, code):
            if code:
                self.stdout.write(f"{keep.id}  error {code}")
            elif verdict is None:
                self.stdout.write(f"{keep.id}  invalid answer")
            elif verdict.is_milestone:
                self.stdout.write(f"{keep.id}  milestone  {verdict.label}")
            else:
                self.stdout.write(f"{keep.id}  no")

        try:
            with scan.scan_lock():
                if rescan and not dry_run:
                    deleted, _ = MilestoneSuggestion.objects.filter(
                        circle=target, status=MilestoneSuggestion.Status.NOT_MILESTONE
                    ).delete()
                    self.stdout.write(f"Deleted {deleted} not-a-milestone rows.")
                summary = scan.scan_circle(
                    target.id,
                    config,
                    limit=limit,
                    dry_run=dry_run,
                    include_album=include_album,
                    include_not_milestone=rescan and dry_run,
                    on_result=report,
                )
                if not dry_run:
                    scan.record_run(ai_settings, summary, trigger="command")
        except scan.ScanRunning:
            raise CommandError("Another milestone scan is running; try again later.") from None

        stopped = f", stopped: {summary.stopped}" if summary.stopped else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Dry run: ' if dry_run else ''}{summary.calls} calls, {summary.proposed} milestones, "
                f"{summary.not_milestone} not, {summary.invalid} invalid, {summary.failed} failed, "
                f"{summary.skipped_birthday} birthday and {summary.skipped_empty} empty posts skipped{stopped}."
            )
        )
