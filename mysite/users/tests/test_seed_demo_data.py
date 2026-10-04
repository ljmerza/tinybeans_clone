from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from mysite.users.management.commands.seed_demo_data import DEFAULT_PASSWORD
from mysite.users.models import User

SEEDED_EMAILS = [
    "superadmin@example.com",
    "guardian@example.com",
    "member@example.com",
    "teen@example.com",
    "second@example.com",
    "solo@example.com",
]


class SeedDemoDataPasswordTests(TestCase):
    def test_new_accounts_get_the_default_password(self):
        call_command("seed_demo_data", stdout=StringIO())

        for email in SEEDED_EMAILS:
            self.assertTrue(User.objects.get(email=email).check_password(DEFAULT_PASSWORD), email)

    def test_reseeding_keeps_a_changed_password(self):
        call_command("seed_demo_data", stdout=StringIO())
        for email in SEEDED_EMAILS:
            user = User.objects.get(email=email)
            user.set_password("a-much-stronger-password")
            user.save(update_fields=["password"])

        call_command("seed_demo_data", stdout=StringIO())

        for email in SEEDED_EMAILS:
            user = User.objects.get(email=email)
            self.assertTrue(user.check_password("a-much-stronger-password"), email)
            self.assertFalse(user.check_password(DEFAULT_PASSWORD), email)
