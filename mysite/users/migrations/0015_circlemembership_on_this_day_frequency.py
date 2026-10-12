from django.db import migrations, models


def copy_account_frequency(apps, schema_editor):
    """Start every membership at its member's account-wide choice."""
    CircleMembership = apps.get_model("users", "CircleMembership")
    User = apps.get_model("users", "User")
    for frequency in (
        User.objects.exclude(on_this_day_frequency="normal").values_list("on_this_day_frequency", flat=True).distinct()
    ):
        CircleMembership.objects.filter(user__on_this_day_frequency=frequency).update(on_this_day_frequency=frequency)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_user_on_this_day_frequency"),
    ]

    operations = [
        migrations.AddField(
            model_name="circlemembership",
            name="on_this_day_frequency",
            field=models.CharField(
                choices=[("off", "Off"), ("less", "Less often"), ("normal", "Normal"), ("more", "More often")],
                default="normal",
                help_text='How often this member sees "On this day" memories from this circle in their home feed',
                max_length=10,
            ),
        ),
        migrations.RunPython(copy_account_frequency, migrations.RunPython.noop),
    ]
