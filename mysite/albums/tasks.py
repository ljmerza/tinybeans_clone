"""Album background tasks."""

from datetime import date

from celery import shared_task
from celery.utils.log import get_task_logger

from mysite import project_logging

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
