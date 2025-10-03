"""Tests for the Celery email task wrapper."""
from unittest.mock import patch

from django.test import SimpleTestCase

from emails.tasks import send_email_task


class SendEmailTaskTests(SimpleTestCase):
    @patch('emails.tasks.email_dispatch_service')
    def test_send_email_task_delegates_to_service(self, mock_service):
        mock_service.send_email.return_value = True

        send_email_task.run(
            to_email='user@example.com',
            template_id='test_template',
            context={'key': 'value'},
        )

        mock_service.send_email.assert_called_once_with(
            to_email='user@example.com',
            template_id='test_template',
            context={'key': 'value'},
        )

    @patch('emails.tasks.email_dispatch_service')
    def test_send_email_task_returns_on_missing_template(self, mock_service):
        mock_service.send_email.return_value = False

        result = send_email_task.run(
            to_email='missing@example.com',
            template_id='missing_template',
            context={},
        )

        self.assertIsNone(result)
        mock_service.send_email.assert_called_once()

    @patch('emails.tasks.email_dispatch_service')
    def test_send_email_task_propagates_exceptions(self, mock_service):
        mock_service.send_email.side_effect = RuntimeError('boom')

        with self.assertRaises(RuntimeError):
            send_email_task.run(
                to_email='boom@example.com',
                template_id='boom_template',
                context={},
            )

        mock_service.send_email.assert_called_once()
