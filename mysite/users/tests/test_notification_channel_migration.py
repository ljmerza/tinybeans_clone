"""Tests for the migration that turns the single notification channel into on/off switches."""

import pytest
from django.db import connection, migrations
from django.db.migrations.loader import MigrationLoader
from django.test import override_settings

from mysite.users.models import User, UserNotificationPreferences

# Columns this migration's models have that later migrations dropped.
OLD_COLUMNS = (
    "channel varchar(20) NOT NULL DEFAULT 'email'",
    "notify_new_media boolean NOT NULL DEFAULT TRUE",
    "notify_comments boolean NOT NULL DEFAULT TRUE",
    "notify_replies boolean NOT NULL DEFAULT TRUE",
    "notify_likes boolean NOT NULL DEFAULT TRUE",
    "email_enabled boolean NOT NULL DEFAULT TRUE",
    "sms_enabled boolean NOT NULL DEFAULT FALSE",
    "push_enabled boolean NOT NULL DEFAULT FALSE",
)


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
    """Historical apps just before the data step, with the old columns back in the table.

    Tests run without migrations, so the table has the current schema; the
    columns are re-added inside the test transaction and rolled back after.
    """
    loader, key, migration, run_python = _find_migration()
    state = loader.project_state(key, at_end=False)
    for operation in migration.operations:
        if operation is run_python:
            break
        operation.state_forwards("users", state)
    with connection.cursor() as cursor:
        for column in OLD_COLUMNS:
            cursor.execute(f"ALTER TABLE users_usernotificationpreferences ADD COLUMN {column}")
    return state.apps, run_python


def create_row(apps, user, circle_id=None, **old_values):
    """A preferences row with ``old_values`` set, as the historical model.

    Inserted through the current model, which fills in the columns later
    migrations added (the historical model doesn't know them).
    """
    row = UserNotificationPreferences.objects.create(user=user, circle_id=circle_id)
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    Preferences.objects.filter(pk=row.pk).update(**old_values)
    return Preferences.objects.get(pk=row.pk)


@pytest.mark.django_db
def test_channel_choice_becomes_its_switch(historical):
    apps, run_python = historical
    by_email = create_row(apps, User.objects.create_user(email="e@example.com"), channel="email")
    by_sms = create_row(apps, User.objects.create_user(email="s@example.com"), channel="sms")

    run_python.code(apps, None)

    by_email.refresh_from_db()
    by_sms.refresh_from_db()
    assert (by_email.email_enabled, by_email.sms_enabled, by_email.push_enabled) == (True, False, False)
    assert (by_sms.email_enabled, by_sms.sms_enabled, by_sms.push_enabled) == (False, True, False)


@pytest.mark.django_db
def test_circle_overrides_are_mapped_too(historical):
    apps, run_python = historical
    Circle = apps.get_model("users", "Circle")
    user = User.objects.create_user(email="o@example.com")
    circle = Circle.objects.create(name="Family", slug="family", created_by_id=user.id)
    create_row(apps, user, channel="email")
    override = create_row(apps, user, circle_id=circle.id, channel="sms")

    run_python.code(apps, None)

    override.refresh_from_db()
    assert (override.email_enabled, override.sms_enabled) == (False, True)


@pytest.mark.django_db
def test_reverse_keeps_texting_users_on_sms(historical):
    apps, run_python = historical
    texting = create_row(apps, User.objects.create_user(email="t@example.com"), sms_enabled=True, email_enabled=True)
    pushing = create_row(apps, User.objects.create_user(email="p@example.com"), email_enabled=False, push_enabled=True)

    run_python.reverse_code(apps, None)

    texting.refresh_from_db()
    pushing.refresh_from_db()
    assert texting.channel == "sms"
    assert pushing.channel == "email"
