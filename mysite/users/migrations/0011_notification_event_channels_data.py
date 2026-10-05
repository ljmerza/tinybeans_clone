from django.db import migrations

EVENTS = ('new_media', 'comments', 'replies', 'likes')
CHANNELS = ('email', 'sms', 'push')


def toggles_to_event_channels(apps, schema_editor):
    # An event goes out on a channel when both its old event flag and the channel's switch were on.
    UserNotificationPreferences = apps.get_model('users', 'UserNotificationPreferences')
    UserNotificationPreferences.objects.update(**{f'{event}_{channel}': False for event in EVENTS for channel in CHANNELS})
    for event in EVENTS:
        for channel in CHANNELS:
            UserNotificationPreferences.objects.filter(**{f'notify_{event}': True, f'{channel}_enabled': True}).update(
                **{f'{event}_{channel}': True}
            )


def event_channels_to_toggles(apps, schema_editor):
    # Back to two dimensions: an event is on if any of its channels is, and a channel is on if any event uses it.
    UserNotificationPreferences = apps.get_model('users', 'UserNotificationPreferences')
    UserNotificationPreferences.objects.update(
        **{f'notify_{event}': False for event in EVENTS}, **{f'{channel}_enabled': False for channel in CHANNELS}
    )
    for event in EVENTS:
        for channel in CHANNELS:
            UserNotificationPreferences.objects.filter(**{f'{event}_{channel}': True}).update(
                **{f'notify_{event}': True, f'{channel}_enabled': True}
            )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_notification_event_channels'),
    ]

    operations = [
        migrations.RunPython(toggles_to_event_channels, event_channels_to_toggles),
    ]
