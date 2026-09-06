"""Link keeps to child profiles from the child-name tags the Tinybeans sync wrote.

A tag matches a child in the keep's circle when it equals the first word of
the profile's display name (case-insensitive). Idempotent.
"""
from django.db import migrations


def backfill_keep_children(apps, schema_editor):
    Keep = apps.get_model('keeps', 'Keep')
    ChildProfile = apps.get_model('users', 'ChildProfile')

    profiles_by_circle = {}
    for profile in ChildProfile.objects.all():
        first = (profile.display_name or '').strip().split(' ')[0].lower()
        if first:
            profiles_by_circle.setdefault(profile.circle_id, {}).setdefault(first, profile.id)

    for keep in Keep.objects.exclude(tags='').only('id', 'circle_id', 'tags'):
        by_first = profiles_by_circle.get(keep.circle_id) or {}
        wanted = {
            by_first[tag.strip().lower()]
            for tag in keep.tags.split(',')
            if tag.strip().lower() in by_first
        }
        if wanted:
            keep.children.add(*wanted)


class Migration(migrations.Migration):

    dependencies = [
        ('keeps', '0007_keep_children'),
        ('users', '0002_add_circle_owner_field'),
    ]

    operations = [
        migrations.RunPython(backfill_keep_children, migrations.RunPython.noop),
    ]
