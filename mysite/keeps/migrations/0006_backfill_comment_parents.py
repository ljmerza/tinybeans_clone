"""Link imported Tinybeans replies to their parent comments.

Reply import records carry the remote parent id in ``payload['parentId']``;
the parent's own record maps that id to the local comment. Idempotent: only
comments without a parent are touched.
"""
from django.db import migrations


def backfill_comment_parents(apps, schema_editor):
    TinybeansImportRecord = apps.get_model('keeps', 'TinybeansImportRecord')
    KeepComment = apps.get_model('keeps', 'KeepComment')

    records = TinybeansImportRecord.objects.filter(
        object_type='comment', comment__isnull=False, comment__parent__isnull=True,
    ).exclude(payload__parentId=None)
    parent_ids = {str(r.payload['parentId']) for r in records if r.payload.get('parentId') is not None}
    parents = {
        r.tinybeans_id: r.comment_id
        for r in TinybeansImportRecord.objects.filter(
            object_type='comment', tinybeans_id__in=parent_ids, comment__isnull=False,
        )
    }
    for record in records:
        parent_comment_id = parents.get(str(record.payload.get('parentId')))
        if parent_comment_id and parent_comment_id != record.comment_id:
            KeepComment.objects.filter(pk=record.comment_id).update(parent_id=parent_comment_id)


class Migration(migrations.Migration):

    dependencies = [
        ('keeps', '0005_keepcomment_parent'),
    ]

    operations = [
        migrations.RunPython(backfill_comment_parents, migrations.RunPython.noop),
    ]
