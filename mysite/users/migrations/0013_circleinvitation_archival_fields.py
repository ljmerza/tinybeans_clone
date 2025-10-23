from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0012_circleinvitation_reminder_sent_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='circleinvitation',
            name='archived_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='circleinvitation',
            name='archived_reason',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddIndex(
            model_name='circleinvitation',
            index=models.Index(fields=['circle', 'archived_at'], name='circle_archived_idx'),
        ),
    ]
