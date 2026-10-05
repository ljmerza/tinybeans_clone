"""Tests for the migration that turns event flags and channel switches into one switch per event and channel."""

import pytest
from django.db import connection, migrations
from django.db.migrations.loader import MigrationLoader
from django.test import override_settings

from mysite.users.models import User

OLD_COLUMNS = {
    "notify_new_media": True,
    "notify_comments": True,
    "notify_replies": True,
    "notify_likes": True,
    "email_enabled": True,
    "sms_enabled": False,
    "push_enabled": False,
}


def _find_migration():
    """The users migration that runs ``toggles_to_event_channels``, whatever number it ends up with."""
    # Tests run with --no-migrations, which hides the migration modules; load them anyway.
    with override_settings(MIGRATION_MODULES={}):
        loader = MigrationLoader(connection, ignore_no_migrations=True)
    for key, migration in loader.disk_migrations.items():
        if key[0] != "users":
            continue
        for operation in migration.operations:
            if isinstance(operation, migrations.RunPython) and operation.code.__name__ == "toggles_to_event_channels":
                return loader, key, migration, operation
    raise AssertionError("toggles_to_event_channels migration not found")


@pytest.fixture
def historical():
    """Historical apps just before the data step, with the old flag and switch columns back in the table.

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
        for column, default in OLD_COLUMNS.items():
            cursor.execute(
                f"ALTER TABLE users_usernotificationpreferences ADD COLUMN {column} boolean NOT NULL "
                f"DEFAULT {'TRUE' if default else 'FALSE'}"
            )
    return state.apps, run_python


def matrix(prefs):
    """The 12 switches as {event: (email, sms, push)}."""
    return {
        event: tuple(getattr(prefs, f"{event}_{channel}") for channel in ("email", "sms", "push"))
        for event in ("new_media", "comments", "replies", "likes")
    }


@pytest.mark.django_db
def test_defaults_become_email_for_every_event(historical):
    apps, run_python = historical
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    prefs = Preferences.objects.create(user_id=User.objects.create_user(email="d@example.com").id)

    run_python.code(apps, None)

    prefs.refresh_from_db()
    assert matrix(prefs) == {
        "new_media": (True, False, False),
        "comments": (True, False, False),
        "replies": (True, False, False),
        "likes": (True, False, False),
    }


@pytest.mark.django_db
def test_event_on_a_channel_needs_both_old_switches(historical):
    apps, run_python = historical
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    prefs = Preferences.objects.create(
        user_id=User.objects.create_user(email="m@example.com").id,
        notify_likes=False,
        notify_comments=False,
        email_enabled=False,
        sms_enabled=True,
        push_enabled=True,
        # The new fields' defaults must not survive the data step.
        likes_email=True,
    )

    run_python.code(apps, None)

    prefs.refresh_from_db()
    assert matrix(prefs) == {
        "new_media": (False, True, True),
        "comments": (False, False, False),
        "replies": (False, True, True),
        "likes": (False, False, False),
    }


@pytest.mark.django_db
def test_circle_overrides_are_mapped_too(historical):
    apps, run_python = historical
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    Circle = apps.get_model("users", "Circle")
    user = User.objects.create_user(email="o@example.com")
    circle = Circle.objects.create(name="Family", slug="family", created_by_id=user.id)
    global_prefs = Preferences.objects.create(user_id=user.id)
    override = Preferences.objects.create(
        user_id=user.id, circle_id=circle.id, notify_new_media=False, email_enabled=False, push_enabled=True
    )

    run_python.code(apps, None)

    global_prefs.refresh_from_db()
    override.refresh_from_db()
    assert matrix(global_prefs)["new_media"] == (True, False, False)
    assert matrix(override) == {
        "new_media": (False, False, False),
        "comments": (False, False, True),
        "replies": (False, False, True),
        "likes": (False, False, True),
    }


@pytest.mark.django_db
def test_reverse_turns_on_events_and_channels_that_any_pair_uses(historical):
    apps, run_python = historical
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    prefs = Preferences.objects.create(
        user_id=User.objects.create_user(email="r@example.com").id,
        new_media_email=False,
        comments_email=False,
        replies_email=False,
        likes_email=False,
        new_media_push=True,
        replies_sms=True,
    )
    silent = Preferences.objects.create(
        user_id=User.objects.create_user(email="s@example.com").id,
        new_media_email=False,
        comments_email=False,
        replies_email=False,
        likes_email=False,
    )

    run_python.reverse_code(apps, None)

    prefs.refresh_from_db()
    silent.refresh_from_db()
    assert (prefs.notify_new_media, prefs.notify_comments, prefs.notify_replies, prefs.notify_likes) == (
        True,
        False,
        True,
        False,
    )
    assert (prefs.email_enabled, prefs.sms_enabled, prefs.push_enabled) == (False, True, True)
    assert (silent.notify_new_media, silent.notify_comments, silent.notify_replies, silent.notify_likes) == (
        False,
        False,
        False,
        False,
    )
    assert (silent.email_enabled, silent.sms_enabled, silent.push_enabled) == (False, False, False)


@pytest.mark.django_db
def test_reverse_keeps_default_rows_on_email(historical):
    apps, run_python = historical
    Preferences = apps.get_model("users", "UserNotificationPreferences")
    prefs = Preferences.objects.create(user_id=User.objects.create_user(email="e@example.com").id)

    run_python.reverse_code(apps, None)

    prefs.refresh_from_db()
    assert (prefs.notify_new_media, prefs.notify_comments, prefs.notify_replies, prefs.notify_likes) == (
        True,
        True,
        True,
        True,
    )
    assert (prefs.email_enabled, prefs.sms_enabled, prefs.push_enabled) == (True, False, False)
