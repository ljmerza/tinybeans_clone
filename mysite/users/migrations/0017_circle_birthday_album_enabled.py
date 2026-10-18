from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0016_remove_user_on_this_day_frequency"),
    ]

    operations = [
        migrations.AddField(
            model_name="circle",
            name="birthday_album_enabled",
            field=models.BooleanField(
                db_default=False,
                default=False,
                help_text="Keep a \"Birthdays\" album of the posts around each child's birthday (needs their "
                "birthdate)",
            ),
        ),
    ]
