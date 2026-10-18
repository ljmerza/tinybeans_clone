"""Link each circle's existing "Milestones" album as its MilestoneAlbum.

Only a circle with exactly one album named "Milestones" (any case) is linked.
Circles with none or several are skipped and logged; a superuser can link
those by hand in Django admin. Reversing does nothing.
"""

import logging

from django.db import migrations
from django.db.models import Count

logger = logging.getLogger(__name__)

ALBUM_NAME = "Milestones"


def link_existing_milestones_albums(apps, schema_editor):
    Album = apps.get_model("albums", "Album")
    MilestoneAlbum = apps.get_model("albums", "MilestoneAlbum")

    matches = Album.objects.filter(name__iexact=ALBUM_NAME)
    counts = matches.values("circle_id").annotate(total=Count("id")).order_by("circle_id")
    for row in counts:
        circle_id = row["circle_id"]
        if row["total"] != 1:
            logger.warning("Skipped linking a Milestones album for circle %s: %s albums match", circle_id, row["total"])
            continue
        album = matches.get(circle_id=circle_id)
        _, created = MilestoneAlbum.objects.get_or_create(circle_id=circle_id, defaults={"album": album})
        if created:
            logger.info("Linked album %s as the Milestones album of circle %s", album.pk, circle_id)


class Migration(migrations.Migration):
    dependencies = [
        ("albums", "0004_milestonealbum_milestonesuggestion"),
    ]

    operations = [
        migrations.RunPython(link_existing_milestones_albums, migrations.RunPython.noop),
    ]
