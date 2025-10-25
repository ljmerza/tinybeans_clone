"""Backfill archived metadata for circle invitations.

This migration reconciles existing databases that were missing the
``archived_at``/``archived_reason`` columns because the fields were added to
the model without a corresponding schema migration. New databases already have
the correct schema from ``0001_initial``, so the statements use
``IF NOT EXISTS`` guards to remain idempotent.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE users_circleinvitation
                ADD COLUMN IF NOT EXISTS archived_at timestamptz NULL
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                ALTER TABLE users_circleinvitation
                ADD COLUMN IF NOT EXISTS archived_reason varchar(100) NULL
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS users_circl_circle__325fa5_idx
                ON users_circleinvitation (circle_id, archived_at)
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
