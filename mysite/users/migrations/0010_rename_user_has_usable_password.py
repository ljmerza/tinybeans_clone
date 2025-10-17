from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0009_user_circle_onboarding_status_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="user",
            old_name="has_usable_password",
            new_name="password_login_enabled",
        ),
    ]
