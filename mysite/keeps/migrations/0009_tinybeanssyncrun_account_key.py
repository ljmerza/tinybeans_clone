"""Key each Tinybeans sync run to the account that produced it.

Several accounts can now be synced from one deployment, and each needs its own
``--since-last-run`` cursor: without this column one account's successful run
would move every other account's cutoff forward and silently skip entries.
"""

import os

from django.db import migrations, models


def claim_existing_runs(apps, schema_editor):
    """Give pre-existing runs to the single account that must have made them.

    Before this migration there was only ever one account, configured through
    TINYBEANS_EMAIL. Claiming its history keeps the first run after the upgrade
    incremental instead of re-walking every journal from the beginning. When
    that variable is unset (CI, a fresh install) there is nothing to claim.
    """
    email = (os.environ.get("TINYBEANS_EMAIL") or "").strip()
    if not email:
        return
    apps.get_model("keeps", "TinybeansSyncRun").objects.filter(account_key="").update(account_key=email)


class Migration(migrations.Migration):
    dependencies = [
        ("keeps", "0008_backfill_keep_children"),
    ]

    operations = [
        migrations.AddField(
            model_name="tinybeanssyncrun",
            name="account_key",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Which configured Tinybeans account this run belongs to (its email, normally).",
                max_length=254,
            ),
        ),
        migrations.AddIndex(
            model_name="tinybeanssyncrun",
            index=models.Index(fields=["account_key", "status", "-started_at"], name="keeps_tinyb_sync_acct_idx"),
        ),
        migrations.RunPython(claim_existing_runs, migrations.RunPython.noop),
    ]
