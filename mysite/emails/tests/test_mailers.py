from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from emails.mailers import MailerConfigurationError, send_via_mailjet


class MailjetMailerTests(SimpleTestCase):
    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='key',
        MAILJET_API_SECRET='secret',
        MAILJET_API_URL='https://api.mailjet.com/v3.1/send',
        MAILJET_FROM_EMAIL='sender@example.com',
        MAILJET_FROM_NAME='Sender',
        MAILJET_USE_SANDBOX=False,
    )
    @patch('emails.mailers.requests.post')
    def test_mailjet_send_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'Messages': [{'Status': 'success'}]}

        send_via_mailjet(
            to_email='recipient@example.com',
            subject='Subject',
            body='Body',
            template_id='template',
        )

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        self.assertEqual(call_kwargs['auth'], ('key', 'secret'))
        self.assertEqual(call_kwargs['json']['Messages'][0]['To'][0]['Email'], 'recipient@example.com')

    @override_settings(MAILJET_ENABLED=False)
    def test_mailjet_without_config_raises(self):
        with self.assertRaises(MailerConfigurationError):
            send_via_mailjet(
                to_email='recipient@example.com',
                subject='Subject',
                body='Body',
                template_id='template',
            )
