from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    """Register circle domain models under the circles app without touching data."""

    initial = True

    dependencies = [
        ('users', '0012_circleinvitation_reminder_sent_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='Circle',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=255)),
                        ('slug', models.SlugField(max_length=255, unique=True)),
                        ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                        ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='circles_created', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'ordering': ['name'],
                        'db_table': 'users_circle',
                    },
                ),
                migrations.CreateModel(
                    name='CircleMembership',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('role', models.CharField(choices=[('admin', 'Circle Admin'), ('member', 'Circle Member')], default='member', max_length=20)),
                        ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                        ('circle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='circles.circle')),
                        ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='memberships_invited', to=settings.AUTH_USER_MODEL)),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='circle_memberships', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'ordering': ['circle__name', 'user__username'],
                        'unique_together': {('user', 'circle')},
                        'db_table': 'users_circlemembership',
                    },
                ),
                migrations.CreateModel(
                    name='CircleInvitation',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('email', models.EmailField(max_length=254)),
                        ('role', models.CharField(choices=[('admin', 'Circle Admin'), ('member', 'Circle Member')], default='member', max_length=20)),
                        ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('cancelled', 'Cancelled'), ('expired', 'Expired')], default='pending', max_length=20)),
                        ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                        ('responded_at', models.DateTimeField(blank=True, null=True)),
                        ('reminder_sent_at', models.DateTimeField(blank=True, null=True)),
                        ('circle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='circles.circle')),
                        ('invited_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='circle_invitations_sent', to=settings.AUTH_USER_MODEL)),
                        ('invited_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='circle_invitations_received', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'users_circleinvitation',
                    },
                ),
                migrations.AddIndex(
                    model_name='circleinvitation',
                    index=models.Index(fields=['circle', 'email'], name='users_circl_circle__fb8341_idx'),
                ),
                migrations.AddIndex(
                    model_name='circleinvitation',
                    index=models.Index(fields=['circle', 'invited_user'], name='users_circle_invited_user_idx'),
                ),
                migrations.AddIndex(
                    model_name='circleinvitation',
                    index=models.Index(fields=['status', 'reminder_sent_at'], name='users_invitation_reminder_idx'),
                ),
            ],
        ),
    ]

