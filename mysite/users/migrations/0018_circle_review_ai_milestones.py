from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0017_circle_birthday_album_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="circle",
            name="review_ai_milestones",
            field=models.BooleanField(
                db_default=False,
                default=False,
                help_text='Hold AI and API token milestone picks for an admin\'s approval instead of adding them to the "Milestones" album straight away',
            ),
        ),
    ]
