from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_circleinvitation_invited_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='circleinvitation',
            name='reminder_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='circleinvitation',
            index=models.Index(fields=['status', 'reminder_sent_at'], name='users_invitation_reminder_idx'),
        ),
    ]
