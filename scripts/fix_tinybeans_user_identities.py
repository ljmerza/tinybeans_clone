"""One-off: give already-imported Tinybeans users their real emails and names.

TEMPORARY — delete once it has been run against every environment. Syncs from
now on pick identities up from the journal followers list themselves (see
``_sync_followers`` in ``sync_tinybeans``); this only repairs users imported
before that existed, including the one case the sync deliberately won't touch:
a placeholder whose real email already belongs to a local account, which gets
merged into that account here.

For every account in TINYBEANS_ACCOUNTS_FILE (or the TINYBEANS_* env vars) it
reads each journal's followers, then for each imported Tinybeans user:

* fills in blank first/last names (existing names are kept),
* replaces a ``tinybeans-<id>@tinybeans-import.invalid`` email with the real one,
* or, when that real email already has a local account, moves everything the
  placeholder owns (keeps, comments, reactions, memberships, import records)
  onto that account and deletes the placeholder. Rows that would collide with
  one the account already has (same reaction on the same keep, same circle
  membership) are dropped as duplicates.

Dry run by default; pass --apply to write. Run inside the web container:

    docker compose exec -T web python scripts/fix_tinybeans_user_identities.py
    docker compose exec -T web python scripts/fix_tinybeans_user_identities.py --apply
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django  # noqa: E402

django.setup()

from django.db import IntegrityError, transaction  # noqa: E402

from mysite.keeps.management.commands.sync_tinybeans import (  # noqa: E402
    PLACEHOLDER_EMAIL_DOMAIN,
    TinybeansClient,
)
from mysite.keeps.models import TinybeansImportRecord, TinybeansObjectType  # noqa: E402
from mysite.keeps.tinybeans_accounts import load_accounts  # noqa: E402
from mysite.users.models.user import User  # noqa: E402


def is_placeholder(email):
    return email.endswith(f"@{PLACEHOLDER_EMAIL_DOMAIN}")


def fetch_follower_users():
    """Tinybeans user id -> full remote user (with emailAddress), across all accounts."""
    remote = {}
    for account in load_accounts():
        client = TinybeansClient()
        if account.token:
            client.set_token(account.token)
        else:
            client.login(account.email, account.password)
        journal_ids = list(account.families) or [
            str(f["journal"]["id"]) for f in client.followings() if f.get("journal")
        ]
        for journal_id in journal_ids:
            for follower in client.followers(journal_id):
                user_id = str((follower.get("user") or {}).get("id") or "")
                if not user_id or user_id in remote:
                    continue
                remote[user_id] = {**follower["user"], **client.follower_user(journal_id, follower["id"])}
            print(f"Journal {journal_id}: {len(remote)} followers so far (account {account.key})")
    return remote


def fill_names(user, remote_user):
    changed = []
    for field, key in (("first_name", "firstName"), ("last_name", "lastName")):
        value = (remote_user.get(key) or "").strip()
        if value and not getattr(user, field):
            setattr(user, field, value)
            changed.append(field)
    return changed


def merge_user(src, dst, apply):
    """Re-point every row referencing ``src`` at ``dst``; return per-relation counts."""
    summary = []
    for rel in User._meta.related_objects:
        if rel.many_to_many:
            continue
        model, field = rel.related_model, rel.field.name
        rows = model._default_manager.filter(**{field: src})
        total = rows.count()
        if not total:
            continue
        moved = dropped = 0
        if apply:
            for pk in list(rows.values_list("pk", flat=True)):
                try:
                    with transaction.atomic():
                        # queryset update: no save() side effects (auto_now, signals) on thousands of keeps
                        model._default_manager.filter(pk=pk).update(**{field: dst})
                    moved += 1
                except IntegrityError:  # dst already has the equivalent row
                    model._default_manager.get(pk=pk).delete()
                    dropped += 1
        summary.append(
            f"{model._meta.label}.{field}: {total}" + (f" (moved {moved}, dropped {dropped})" if apply else "")
        )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    apply = parser.parse_args().apply

    remote_users = fetch_follower_users()
    records = TinybeansImportRecord.objects.filter(object_type=TinybeansObjectType.USER).select_related("user")

    with transaction.atomic():
        for record in records.order_by("tinybeans_id"):
            user = record.user
            if user is None:
                continue
            remote_user = remote_users.get(record.tinybeans_id)
            label = f"Tinybeans {record.tinybeans_id} (local #{user.pk} {user.email})"
            if remote_user is None:
                if is_placeholder(user.email) or not user.first_name:
                    print(f"SKIP   {label}: not a follower of any synced journal, nothing to fill in from")
                continue

            email = (remote_user.get("emailAddress") or "").strip().lower()
            target = user
            if email and is_placeholder(user.email):
                existing = User.objects.filter(email__iexact=email).exclude(pk=user.pk).first()
                if existing:
                    target = existing
                    print(f"MERGE  {label} -> local #{existing.pk} {existing.email}")
                    for line in merge_user(user, existing, apply):
                        print(f"         {line}")
                else:
                    print(f"EMAIL  {label} -> {email}")
                    if apply:
                        user.email = email
                        user.save(update_fields=["email"])

            changed = fill_names(target, remote_user)
            if changed:
                print(f"NAME   {label}: {target.first_name} {target.last_name}".rstrip())
                if apply:
                    target.save(update_fields=changed)

            if apply:
                if target != user:
                    record.refresh_from_db()  # the merge re-pointed record.user already
                    user.delete()
                remote = {k: remote_user.get(k) for k in ("emailAddress", "firstName", "lastName", "username")}
                record.payload = {**record.payload, **{k: v for k, v in remote.items() if v}}
                record.save(update_fields=["payload", "updated_at"])

    print("Applied." if apply else "Dry run; nothing written. Re-run with --apply to write.")


if __name__ == "__main__":
    main()
