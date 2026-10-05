"""Give the import bookkeeping models source-neutral names.

Renames the models (and so their tables), the remote id field, the indexes and
the reverse accessors. No data changes. RenameField doesn't carry
``Meta.indexes`` along, so the (object_type, id) index is dropped and
re-created under its new name.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keeps', '0015_backfill_people_from_children'),
        ('users', '0006_notification_email_digest'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='tinybeansimportrecord',
            name='keeps_tinyb_object__idx',
        ),
        migrations.RenameModel(
            old_name='TinybeansImportRecord',
            new_name='ImportRecord',
        ),
        migrations.RenameModel(
            old_name='TinybeansSyncRun',
            new_name='ImportSyncRun',
        ),
        migrations.RenameField(
            model_name='importrecord',
            old_name='tinybeans_id',
            new_name='source_id',
        ),
        migrations.AddIndex(
            model_name='importrecord',
            index=models.Index(fields=['object_type', 'source_id'], name='keeps_import_object_idx'),
        ),
        migrations.RenameIndex(
            model_name='importsyncrun',
            new_name='keeps_import_sync_acct_idx',
            old_name='keeps_tinyb_sync_acct_idx',
        ),
        migrations.AlterField(
            model_name='importrecord',
            name='child',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='import_records', to='users.childprofile'),
        ),
        migrations.AlterField(
            model_name='importrecord',
            name='circle',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='import_records', to='users.circle'),
        ),
        migrations.AlterField(
            model_name='importrecord',
            name='comment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='import_records', to='keeps.keepcomment'),
        ),
        migrations.AlterField(
            model_name='importrecord',
            name='keep',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='import_records', to='keeps.keep'),
        ),
        migrations.AlterField(
            model_name='importrecord',
            name='reaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='import_records', to='keeps.keepreaction'),
        ),
        migrations.AlterField(
            model_name='importrecord',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='import_records', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='importsyncrun',
            name='account_key',
            field=models.CharField(blank=True, default='', help_text='Which configured import account this run belongs to (its email, normally).', max_length=254),
        ),
    ]
