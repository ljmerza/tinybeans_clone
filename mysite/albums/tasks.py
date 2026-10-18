"""Album background tasks."""

from datetime import date

from celery import shared_task
from celery.utils.log import get_task_logger

from mysite import project_logging

from .birthdays import sync_enabled_circles
from .recaps import beat_today, create_recaps_for_enabled_circles, previous_month

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=15 * 60)
def create_monthly_recaps(self, month: str | None = None):
    """Make last month's recap album in every circle that turned them on (run by beat on the 1st).

    ``month`` (YYYY-MM-DD) pins the month, so a retry redoes the same month
    even if it runs after midnight. Circles already done are skipped, so a
    retry only redoes the ones that failed.
    """
    target = date.fromisoformat(month) if month else previous_month(beat_today())
    with project_logging.log_context(task="albums.create_monthly_recaps", month=target.isoformat()):
        made, failed = create_recaps_for_enabled_circles(target)
        logger.info("Created %s monthly recaps for %s", made, f"{target:%Y-%m}")
        if failed:
            raise self.retry(kwargs={"month": target.isoformat()})
        return made


@shared_task(bind=True, max_retries=3, default_retry_delay=15 * 60)
def sync_birthday_albums(self, circle_id: int | None = None):
    """Add new birthday posts to the Birthdays album of every circle that turned it on (run by beat nightly).

    ``circle_id`` limits it to one circle; that is how turning the setting on
    or setting a child's birthdate backfills right away. A retry redoes only
    what is missing, since posts already added are skipped.
    """
    with project_logging.log_context(task="albums.sync_birthday_albums", circle_id=circle_id):
        added, failed = sync_enabled_circles(circle_id)
        logger.info("Added %s posts to birthdays albums", added)
        if failed:
            raise self.retry(kwargs={"circle_id": circle_id})
        return added


@shared_task(bind=True, soft_time_limit=50 * 60, time_limit=55 * 60, max_retries=4, default_retry_delay=15 * 60)
def scan_milestones(self, circle_id: int | None = None):
    """Ask the operator's AI model which new posts are milestones, in every circle that turned AI on (run by beat).

    ``circle_id`` limits it to one circle; that is the admin's "Scan now". It
    runs on the ``ai`` queue under a global lock, so only one scan talks to the
    model at a time. A failed post is simply tried again next run. The one
    retry: when the nightly run finds an admin's scan holding the lock, it
    tries again every 15 minutes (4 times, longer than a scan can run), so one
    circle's "Scan now" can't cost every other circle its night. The limits
    override the 30s/40s defaults; a soft time limit stops it cleanly and
    keeps what it wrote (see ``mysite.ai.scan``).
    """
    from mysite.ai.scan import run_scan

    trigger = "beat" if circle_id is None else "admin"
    with project_logging.log_context(task="albums.scan_milestones", circle_id=circle_id):
        results = run_scan(circle_id, trigger=trigger)
        if results.get("skipped") == "running" and circle_id is None:
            if self.request.retries < self.max_retries:
                raise self.retry()
            logger.warning("Milestone scan gave up: another scan held the lock all night")
        logger.info("Milestone scan done for %s circles", len(results) if "skipped" not in results else 0)
        return results
