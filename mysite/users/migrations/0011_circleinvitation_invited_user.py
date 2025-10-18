from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_rename_user_has_usable_password'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='circleinvitation',
            name='invited_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='circle_invitations_received',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name='circleinvitation',
            index=models.Index(fields=['circle', 'invited_user'], name='users_circle_invited_user_idx'),
        ),
    ]
