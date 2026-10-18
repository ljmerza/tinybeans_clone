import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("albums", "0003_birthdayalbum"),
        ("keeps", "0018_growthmeasurement"),
        ("users", "0018_circle_review_ai_milestones"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MilestoneAlbum",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "album",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="milestone_album", to="albums.album"
                    ),
                ),
                (
                    "circle",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="milestone_album", to="users.circle"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MilestoneSuggestion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("dismissed", "Dismissed"),
                            ("not_milestone", "Not a milestone"),
                            ("auto_added", "Added automatically"),
                        ],
                        max_length=16,
                    ),
                ),
                ("source", models.CharField(choices=[("ai", "In-app AI"), ("agent", "API token")], max_length=8)),
                ("label", models.CharField(blank=True, max_length=80)),
                ("reason", models.CharField(blank=True, max_length=500)),
                ("model_name", models.CharField(blank=True, max_length=160)),
                ("source_token_prefix", models.CharField(blank=True, max_length=12)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                (
                    "circle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="milestone_suggestions",
                        to="users.circle",
                    ),
                ),
                (
                    "decided_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "keep",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="milestone_suggestion",
                        to="keeps.keep",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["circle", "status", "-created_at"], name="albums_mile_circle__306000_idx")
                ],
            },
        ),
    ]
