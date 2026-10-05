"""Make one circle's monthly recap album by hand, e.g. to backfill past months.

    python manage.py create_monthly_recap family 2026-09

Same rules as the scheduled run (see ``mysite.albums.recaps``), except that it
works whether or not the circle has recaps turned on. A month that already has
a recap, even a deleted one, is left alone.
"""

import re
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from mysite.albums.recaps import beat_today, create_monthly_recap, previous_month, recap_name
from mysite.circles.models import Circle

MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


class Command(BaseCommand):
    help = "Make a circle's recap album of a month's most-liked photos (default: last month)."

    def add_arguments(self, parser):
        parser.add_argument("circle", help="Circle id or slug")
        parser.add_argument("month", nargs="?", help="Month as YYYY-MM; defaults to last month")

    def handle(self, *args, circle, month, **options):
        found = Circle.objects.filter(id=int(circle)) if circle.isdigit() else Circle.objects.filter(slug=circle)
        target_circle = found.first()
        if target_circle is None:
            raise CommandError(f"No circle {circle!r}.")

        if month:
            match = MONTH_RE.match(month)
            if not match or not 1 <= int(match.group(2)) <= 12:
                raise CommandError("Month must be YYYY-MM.")
            target = date(int(match.group(1)), int(match.group(2)), 1)
        else:
            target = previous_month(beat_today())

        album = create_monthly_recap(target_circle, target)
        if album is None:
            self.stdout.write(
                f"No recap made for {recap_name(target)} in {target_circle}: it already has one, "
                "or no photo post there has likes or comments."
            )
            return
        self.stdout.write(
            self.style.SUCCESS(f'Created "{album.name}" in {target_circle} with {album.album_keeps.count()} posts.')
        )
