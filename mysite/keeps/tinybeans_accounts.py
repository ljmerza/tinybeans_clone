"""Accounts the scheduled Tinybeans sync should import.

The nightly task reads its accounts from a YAML file instead of a single
``TINYBEANS_EMAIL`` / ``TINYBEANS_PASSWORD`` pair, so several Tinybeans logins —
each with its own set of families — can be synced by one deployment. Point
``TINYBEANS_ACCOUNTS_FILE`` at the file::

    TINYBEANS_ACCOUNTS_FILE=/app/volumes/tinybeans/accounts.yml

Schema::

    accounts:
      - email: parent@example.com
        password: hunter2
        # owner: local-user@example.com  # local account that owns imported
        #                                # circles; defaults to the email above
        # enabled: false                 # skip without deleting the block
        families:                        # omit (or leave empty) to sync every
          - id: 123456                   # journal the account follows
            name: Merza                  # cosmetic, only used for readability
          - 789012                       # a bare journal id also works

      - email: other@example.com
        token: an-existing-access-token  # instead of password; needs `owner`
        owner: other@example.com

Each account is keyed by its email (or an explicit ``key:``) and that key is
stored on every :class:`~mysite.keeps.models.TinybeansSyncRun`, so one account's
``--since-last-run`` cursor never advances another's.

With no file configured the loader falls back to the legacy ``TINYBEANS_EMAIL`` /
``TINYBEANS_PASSWORD`` (or ``TINYBEANS_ACCESS_TOKEN`` plus ``TINYBEANS_OWNER``)
environment variables and yields at most one account, so ad-hoc runs and older
deployments keep working.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ACCOUNTS_FILE_ENV = "TINYBEANS_ACCOUNTS_FILE"


class TinybeansAccountsError(Exception):
    """The configured accounts file is missing, unreadable or malformed."""


@dataclass(frozen=True)
class TinybeansAccount:
    """One Tinybeans login plus the families (journals) to import from it."""

    key: str
    email: str | None = None
    password: str | None = None
    token: str | None = None
    owner: str | None = None
    families: tuple[str, ...] = ()

    def command_options(self) -> dict[str, Any]:
        """Keyword arguments for ``call_command("sync_tinybeans", ...)``.

        Every credential is passed explicitly (``None`` included) so an account
        never inherits another account's value from the environment defaults on
        the command's own arguments.
        """
        return {
            "account_key": self.key,
            "email": self.email or None,
            "password": self.password or None,
            "token": self.token or None,
            "owner": self.owner or None,
            "journal": list(self.families) or None,
        }


def load_accounts() -> list[TinybeansAccount]:
    """Return every enabled account, from the YAML file or the environment."""
    path = os.environ.get(ACCOUNTS_FILE_ENV, "").strip()
    if not path:
        return _accounts_from_env()
    return _accounts_from_file(Path(path))


def _accounts_from_file(path: Path) -> list[TinybeansAccount]:
    if not path.is_file():
        raise TinybeansAccountsError(f"{ACCOUNTS_FILE_ENV} points at {path}, which is not a readable file")
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise TinybeansAccountsError(f"Could not read {path}: {exc}") from exc

    if isinstance(raw, dict):
        entries = raw.get("accounts") or []
    elif isinstance(raw, list):
        entries = raw
    else:
        raise TinybeansAccountsError(f"{path}: expected a mapping with an 'accounts' list, got {type(raw).__name__}")
    if not isinstance(entries, list):
        raise TinybeansAccountsError(f"{path}: 'accounts' must be a list, got {type(entries).__name__}")

    accounts: list[TinybeansAccount] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        account = _parse_account(entry, f"{path}: accounts[{index}]")
        if account is None:
            continue
        if account.key in seen:
            raise TinybeansAccountsError(
                f"{path}: duplicate account '{account.key}'. Each account needs a unique email "
                "(or an explicit 'key') so its incremental sync cursor stays separate."
            )
        seen.add(account.key)
        accounts.append(account)
    return accounts


def _parse_account(entry: Any, where: str) -> TinybeansAccount | None:
    if not isinstance(entry, dict):
        raise TinybeansAccountsError(f"{where} must be a mapping, got {type(entry).__name__}")
    if not _as_bool(entry.get("enabled", True)):
        return None

    email = _as_str(entry.get("email"))
    password = _as_str(entry.get("password"), strip=False)
    token = _as_str(entry.get("token"))
    owner = _as_str(entry.get("owner"))
    key = _as_str(entry.get("key")) or email or owner
    if not key:
        raise TinybeansAccountsError(f"{where} needs an 'email' (or an explicit 'key')")
    if token:
        if not owner:
            raise TinybeansAccountsError(f"{where} authenticates with 'token', which also requires 'owner'")
    elif not (email and password):
        raise TinybeansAccountsError(f"{where} needs both 'email' and 'password' (or 'token' plus 'owner')")

    return TinybeansAccount(
        key=key,
        email=email or None,
        password=password or None,
        token=token or None,
        owner=owner or None,
        families=_parse_families(entry.get("families"), where),
    )


def _parse_families(value: Any, where: str) -> tuple[str, ...]:
    """Normalise the ``families`` block to journal ids, preserving order."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise TinybeansAccountsError(f"{where}: 'families' must be a list of journal ids, got {type(value).__name__}")

    ids: list[str] = []
    for index, item in enumerate(value):
        journal_id = _as_str(item.get("id") if isinstance(item, dict) else item)
        if not journal_id:
            raise TinybeansAccountsError(f"{where}: families[{index}] needs a journal 'id'")
        if journal_id not in ids:
            ids.append(journal_id)
    return tuple(ids)


def _accounts_from_env() -> list[TinybeansAccount]:
    email = os.environ.get("TINYBEANS_EMAIL", "").strip()
    password = os.environ.get("TINYBEANS_PASSWORD", "")
    token = os.environ.get("TINYBEANS_ACCESS_TOKEN", "").strip()
    owner = os.environ.get("TINYBEANS_OWNER", "").strip()

    if email and password:
        return [TinybeansAccount(key=email, email=email, password=password, owner=owner or None)]
    if token and (owner or email):
        return [TinybeansAccount(key=owner or email, token=token, owner=owner or email)]
    return []


def _as_str(value: Any, *, strip: bool = True) -> str:
    """Coerce a YAML scalar to text; numeric journal ids arrive as ints."""
    if value is None:
        return ""
    text = str(value)
    return text.strip() if strip else text


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
