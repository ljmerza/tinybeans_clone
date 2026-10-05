from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_notification_event_channels_data'),
    ]

    operations = [        migrations.RemoveField(
            model_name='usernotificationpreferences',
            name='notify_new_media',
        ),
        migrations.RemoveField(
            model_name='usernotificationpreferences',
            name='notify_comments',
        ),
        migrations.RemoveField(
            model_name='usernotificationpreferences',
            name='notify_replies',
        ),
        migrations.RemoveField(
            model_name='usernotificationpreferences',
            name='notify_likes',
        ),
        migrations.RemoveField(
            model_name='usernotificationpreferences',
            name='email_enabled',
        ),
        migrations.RemoveField(
            model_name='usernotificationpreferences',
            name='sms_enabled',
        ),
        migrations.RemoveField(
            model_name='usernotificationpreferences',
            name='push_enabled',
        ),
    ]
