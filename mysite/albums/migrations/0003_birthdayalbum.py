import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("albums", "0002_monthlyrecap"),
        ("users", "0017_circle_birthday_album_enabled"),
    ]

    operations = [
        migrations.CreateModel(
            name="BirthdayAlbum",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "album",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="birthday_album", to="albums.album"
                    ),
                ),
                (
                    "circle",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="birthday_album", to="users.circle"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BirthdayAlbumMatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("matched_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "birthday_album",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matches",
                        to="albums.birthdayalbum",
                    ),
                ),
                (
                    "keep",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="+", to="keeps.keep"
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "birthday album matches",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("birthday_album", "keep"), name="albums_unique_birthday_album_match"
                    )
                ],
            },
        ),
    ]
