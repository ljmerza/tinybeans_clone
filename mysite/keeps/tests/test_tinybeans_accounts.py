"""Tests for the YAML accounts file that drives the scheduled Tinybeans sync."""

import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from mysite.keeps.tinybeans_accounts import (
    TinybeansAccountsError,
    load_accounts,
)

NO_ENV = {
    "TINYBEANS_ACCOUNTS_FILE": "",
    "TINYBEANS_EMAIL": "",
    "TINYBEANS_PASSWORD": "",
    "TINYBEANS_ACCESS_TOKEN": "",
    "TINYBEANS_OWNER": "",
}


class LoadAccountsFromFileTests(SimpleTestCase):
    def load(self, body):
        path = Path(tempfile.mkdtemp()) / "accounts.yml"
        path.write_text(body)
        self.addCleanup(shutil.rmtree, path.parent)
        with mock.patch.dict("os.environ", {**NO_ENV, "TINYBEANS_ACCOUNTS_FILE": str(path)}):
            return load_accounts()

    def test_reads_accounts_and_families(self):
        accounts = self.load(
            """
accounts:
  - email: one@example.com
    password: pw1
    families:
      - id: 100
        name: Merza
      - 200
"""
        )
        self.assertEqual(len(accounts), 1)
        account = accounts[0]
        self.assertEqual(account.key, "one@example.com")
        self.assertEqual(account.email, "one@example.com")
        self.assertEqual(account.password, "pw1")
        self.assertEqual(account.owner, None)
        self.assertEqual(account.families, ("100", "200"))

    def test_families_are_optional_and_mean_every_journal(self):
        accounts = self.load("accounts:\n  - email: a@example.com\n    password: pw\n")
        self.assertEqual(accounts[0].families, ())
        self.assertIsNone(accounts[0].command_options()["journal"])

    def test_duplicate_family_ids_are_collapsed_in_order(self):
        accounts = self.load("accounts:\n  - email: a@example.com\n    password: pw\n    families: [300, 100, 300]\n")
        self.assertEqual(accounts[0].families, ("300", "100"))

    def test_bare_list_without_accounts_key_is_accepted(self):
        accounts = self.load("- email: a@example.com\n  password: pw\n")
        self.assertEqual(accounts[0].email, "a@example.com")

    def test_disabled_accounts_are_dropped(self):
        accounts = self.load(
            "accounts:\n"
            "  - email: off@example.com\n    password: pw\n    enabled: false\n"
            "  - email: on@example.com\n    password: pw\n"
        )
        self.assertEqual([a.key for a in accounts], ["on@example.com"])

    def test_token_accounts_need_an_owner(self):
        with self.assertRaisesMessage(TinybeansAccountsError, "requires 'owner'"):
            self.load("accounts:\n  - email: a@example.com\n    token: abc\n")

    def test_token_account_authenticates_without_a_password(self):
        accounts = self.load("accounts:\n  - token: abc\n    owner: a@example.com\n")
        options = accounts[0].command_options()
        self.assertEqual(accounts[0].key, "a@example.com")
        self.assertEqual(options["token"], "abc")
        self.assertIsNone(options["password"])

    def test_account_without_credentials_is_rejected(self):
        with self.assertRaisesMessage(TinybeansAccountsError, "needs both 'email' and 'password'"):
            self.load("accounts:\n  - email: a@example.com\n")

    def test_duplicate_keys_are_rejected(self):
        # Two blocks sharing a key would share an incremental cursor and each
        # silently skip the entries the other already advanced past.
        with self.assertRaisesMessage(TinybeansAccountsError, "duplicate account"):
            self.load(
                "accounts:\n  - email: a@example.com\n    password: pw\n  - email: a@example.com\n    password: pw2\n"
            )

    def test_explicit_key_separates_two_blocks_for_one_email(self):
        accounts = self.load(
            "accounts:\n"
            "  - key: merza\n    email: a@example.com\n    password: pw\n    families: [100]\n"
            "  - key: smith\n    email: a@example.com\n    password: pw\n    families: [200]\n"
        )
        self.assertEqual([a.key for a in accounts], ["merza", "smith"])

    def test_families_must_be_a_list(self):
        with self.assertRaisesMessage(TinybeansAccountsError, "'families' must be a list"):
            self.load("accounts:\n  - email: a@example.com\n    password: pw\n    families: 100\n")

    def test_malformed_yaml_is_reported(self):
        with self.assertRaisesMessage(TinybeansAccountsError, "Could not read"):
            self.load("accounts: [unclosed\n")

    def test_empty_file_yields_no_accounts(self):
        self.assertEqual(self.load(""), [])

    def test_missing_file_is_an_error_not_a_silent_no_op(self):
        with (
            mock.patch.dict("os.environ", {**NO_ENV, "TINYBEANS_ACCOUNTS_FILE": "/nonexistent/accounts.yml"}),
            self.assertRaisesMessage(TinybeansAccountsError, "not a readable file"),
        ):
            load_accounts()


class LoadAccountsFromEnvTests(SimpleTestCase):
    def test_no_credentials_yields_nothing(self):
        with mock.patch.dict("os.environ", NO_ENV):
            self.assertEqual(load_accounts(), [])

    def test_email_and_password_yield_one_account(self):
        env = {**NO_ENV, "TINYBEANS_EMAIL": "a@example.com", "TINYBEANS_PASSWORD": "pw"}
        with mock.patch.dict("os.environ", env):
            accounts = load_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].key, "a@example.com")
        self.assertEqual(accounts[0].families, ())

    def test_token_falls_back_to_the_owner_as_key(self):
        env = {**NO_ENV, "TINYBEANS_ACCESS_TOKEN": "abc", "TINYBEANS_OWNER": "a@example.com"}
        with mock.patch.dict("os.environ", env):
            accounts = load_accounts()
        self.assertEqual(accounts[0].key, "a@example.com")
        self.assertEqual(accounts[0].token, "abc")

    def test_token_without_an_owner_or_email_is_unusable(self):
        with mock.patch.dict("os.environ", {**NO_ENV, "TINYBEANS_ACCESS_TOKEN": "abc"}):
            self.assertEqual(load_accounts(), [])
