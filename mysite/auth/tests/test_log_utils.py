"""Tests for PII-masking log helpers (ADR-015)."""
from django.test import SimpleTestCase

from mysite.auth.log_utils import mask_email, mask_id


class MaskEmailTests(SimpleTestCase):
    def test_masks_local_part_keeps_domain(self):
        self.assertEqual(mask_email('jane.doe@example.com'), 'j***@example.com')

    def test_single_char_local_part(self):
        self.assertEqual(mask_email('a@example.com'), 'a***@example.com')

    def test_none_and_empty_return_placeholder(self):
        self.assertEqual(mask_email(None), '***')
        self.assertEqual(mask_email(''), '***')

    def test_non_email_returns_placeholder(self):
        self.assertEqual(mask_email('notanemail'), '***')

    def test_does_not_leak_full_address(self):
        masked = mask_email('sensitive.user@corp.example')
        self.assertNotIn('sensitive.user', masked)
        self.assertIn('@corp.example', masked)


class MaskIdTests(SimpleTestCase):
    def test_truncates_long_id(self):
        self.assertEqual(mask_id('1234567890', keep=6), '123456...')

    def test_short_id_returned_as_is(self):
        self.assertEqual(mask_id('123', keep=6), '123')

    def test_none_returns_placeholder(self):
        self.assertEqual(mask_id(None), '***')
