"""Tests for the migration that turns the single notification channel into on/off switches."""

import pytest
from django.db import connection, migrations
from django.db.migrations.loader import MigrationLoader
from django.test import override_settings

from mysite.users.models import User


def _find_migration():
    """The users migration that runs ``channel_to_toggles``, whatever number it ends up with."""
    # Tests run with --no-migrations, which hides the migration modules; load them anyway.
    with override_settings(MIGRATION_MODULES={}):
        loader = MigrationLoader(connection, ignore_no_migrations=True)
    for key, migration in loader.disk_migrations.items():
        if key[0] != "users":
            continue
        for operation in migration.operations:
            if isinstance(operation, migrations.RunPython) and operation.code.__name__ == "channel_to_toggles":
                return loader, key, migration, operation
    raise AssertionError("channel_to_toggles migration not found")


@pytest.fixture
def historical():
    """Historical apps just before the data step, with the old ``channel`` column back in the table.

    Tests run without migrations, so the table has the current schema; the
    column is re-added inside the test transaction and rolled back after.
    """
    loader, key, migration, run_python = _find_migration()
    state = loader.project_state(key, at_end=False)
    for operation in migration.operations:
        if operation is run_python:
            break
        operation.state_forwards("users", state)
    with connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE users_usernotificationpreferences ADD COLUMN channel varchar(20) NOT NULL DEFAULT 'email'"
        )
    return state.apps, run_python


@pytest.mark.django_db
def test_channel_choice_becomes_its_switch(historical):
    apps, run_python = historical
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    by_email = Preferences.objects.create(user_id=User.objects.create_user(email="e@example.com").id, channel="email")
    by_sms = Preferences.objects.create(user_id=User.objects.create_user(email="s@example.com").id, channel="sms")

    run_python.code(apps, None)

    by_email.refresh_from_db()
    by_sms.refresh_from_db()
    assert (by_email.email_enabled, by_email.sms_enabled, by_email.push_enabled) == (True, False, False)
    assert (by_sms.email_enabled, by_sms.sms_enabled, by_sms.push_enabled) == (False, True, False)


@pytest.mark.django_db
def test_circle_overrides_are_mapped_too(historical):
    apps, run_python = historical
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    Circle = apps.get_model("users", "Circle")
    user = User.objects.create_user(email="o@example.com")
    circle = Circle.objects.create(name="Family", slug="family", created_by_id=user.id)
    Preferences.objects.create(user_id=user.id, channel="email")
    override = Preferences.objects.create(user_id=user.id, circle_id=circle.id, channel="sms")

    run_python.code(apps, None)

    override.refresh_from_db()
    assert (override.email_enabled, override.sms_enabled) == (False, True)


@pytest.mark.django_db
def test_reverse_keeps_texting_users_on_sms(historical):
    apps, run_python = historical
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    texting = Preferences.objects.create(
        user_id=User.objects.create_user(email="t@example.com").id, sms_enabled=True, email_enabled=True
    )
    pushing = Preferences.objects.create(
        user_id=User.objects.create_user(email="p@example.com").id, email_enabled=False, push_enabled=True
    )

    run_python.reverse_code(apps, None)

    texting.refresh_from_db()
    pushing.refresh_from_db()
    assert texting.channel == "sms"
    assert pushing.channel == "email"
