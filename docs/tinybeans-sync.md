# Tinybeans sync: accounts, families and the nightly schedule

## Where the accounts come from

The scheduled sync (`mysite.keeps.tasks.sync_tinybeans_incremental`) reads a
YAML file whose path comes from `TINYBEANS_ACCOUNTS_FILE`. In Docker that
defaults to `/app/volumes/tinybeans/accounts.yml`, which is gitignored because
it holds plaintext credentials.

```yaml
accounts:
  - email: parent@example.com
    password: hunter2
    # owner: local-user@example.com   # local account that owns imported
    #                                 # circles; defaults to the email above
    # enabled: false                  # skip without deleting the block
    families:                         # omit (or leave empty) to sync every
      - id: 123456                    # journal the account follows
        name: Merza                   # cosmetic, only for readability
      - 789012                        # a bare journal id also works

  - email: other@example.com
    token: an-existing-access-token   # instead of password; requires `owner`
    owner: other@example.com
```

A bare top-level list (no `accounts:` key) is accepted too.

To find journal ids, run a dry run — it prints
`Syncing journal '<name>' (id <n>)...` for every journal the account follows:

```bash
docker compose exec web python manage.py sync_tinybeans --dry-run
```

With no `TINYBEANS_ACCOUNTS_FILE` set, the loader falls back to the older
`TINYBEANS_EMAIL` / `TINYBEANS_PASSWORD` (or `TINYBEANS_ACCESS_TOKEN` plus
`TINYBEANS_OWNER`) environment variables and yields a single account, so ad-hoc
runs still work.

## Per-account sync history

Every `TinybeansSyncRun` records an `account_key` (the account's email, or an
explicit `key:`). `--since-last-run` only looks at runs with the same key, so
one account finishing a sync never advances another account's cutoff. The
"a sync is already running" guard is per-account for the same reason, and one
account failing does not stop the rest of the nightly batch.

Run the command manually for a single account with:

```bash
python manage.py sync_tinybeans --email parent@example.com \
    --journal 123456 --account-key parent@example.com --since-last-run
```

## Shared journals

`TinybeansImportRecord` is unique on `(object_type, tinybeans_id)` across all
accounts. When two accounts follow the same journal it therefore maps to one
local circle, owned by whichever account imported it first, rather than being
duplicated per account.

## Schedule

Beat runs the sync at midnight in `CELERY_TIMEZONE`, which
`docker-compose.yml` sets to `America/New_York`. That is deliberately separate
from Django's `TIME_ZONE` (still `UTC`), so the job runs at local midnight
year-round, DST included, without changing how datetimes are stored or
rendered. The other periodic cleanups are unaffected by the zone in practice
but do now follow it as well.
