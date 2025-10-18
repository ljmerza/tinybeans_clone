from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from mysite.emails.mailers import MailerConfigurationError, MailerSendError, send_via_mailjet


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
    @patch('mysite.emails.mailers.requests.post')
    def test_mailjet_send_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'Messages': [{'Status': 'success'}]}

        send_via_mailjet(
            to_email='recipient@example.com',
            subject='Subject',
            text_body='Body',
            html_body='<p>Body</p>',
            template_id='template',
        )

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        self.assertEqual(call_kwargs['auth'], ('key', 'secret'))
        message = call_kwargs['json']['Messages'][0]
        self.assertEqual(message['To'][0]['Email'], 'recipient@example.com')
        self.assertEqual(message['TextPart'], 'Body')
        self.assertEqual(message['HTMLPart'], '<p>Body</p>')

    @override_settings(MAILJET_ENABLED=False)
    def test_mailjet_without_config_raises(self):
        with self.assertRaises(MailerConfigurationError):
            send_via_mailjet(
                to_email='recipient@example.com',
                subject='Subject',
                text_body='Body',
                html_body=None,
                template_id='template',
            )

    @override_settings(MAILJET_ENABLED=False)
    def test_mailjet_disabled_raises_configuration_error(self):
        with self.assertRaises(MailerConfigurationError) as cm:
            send_via_mailjet(
                to_email='test@example.com',
                subject='Test',
                text_body='Test body',
                html_body=None,
                template_id='test',
            )

        self.assertIn('not configured', str(cm.exception))

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='key',
        MAILJET_API_SECRET='secret',
        MAILJET_FROM_EMAIL='sender@example.com',
        MAILJET_FROM_NAME='Test Sender',
        MAILJET_USE_SANDBOX=True,
        MAILJET_API_URL='https://api.mailjet.com/v3.1/send',
    )
    @patch('mysite.emails.mailers.requests.post')
    def test_mailjet_request_exception(self, mock_post):
        import requests

        mock_post.side_effect = requests.RequestException('Connection error')

        with self.assertRaises(MailerSendError) as cm:
            send_via_mailjet(
                to_email='test@example.com',
                subject='Test',
                text_body='Test body',
                html_body=None,
                template_id='test',
            )

        self.assertIn('Connection error', str(cm.exception))

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='key',
        MAILJET_API_SECRET='secret',
        MAILJET_FROM_EMAIL='sender@example.com',
        MAILJET_FROM_NAME='Test Sender',
        MAILJET_USE_SANDBOX=False,
        MAILJET_API_URL='https://api.mailjet.com/v3.1/send',
    )
    @patch('mysite.emails.mailers.requests.post')
    def test_mailjet_http_error_response(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response

        with self.assertRaises(MailerSendError) as cm:
            send_via_mailjet(
                to_email='test@example.com',
                subject='Test',
                text_body='Test body',
                html_body=None,
                template_id='test',
            )

        self.assertIn('HTTP 400', str(cm.exception))

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='key',
        MAILJET_API_SECRET='secret',
        MAILJET_FROM_EMAIL='sender@example.com',
        MAILJET_FROM_NAME='Test Sender',
        MAILJET_USE_SANDBOX=False,
        MAILJET_API_URL='https://api.mailjet.com/v3.1/send',
    )
    @patch('mysite.emails.mailers.requests.post')
    @patch('mysite.emails.mailers.logger')
    def test_mailjet_success_response(self, mock_logger, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'Messages': [{'Status': 'success'}]}
        mock_post.return_value = mock_response

        send_via_mailjet(
            to_email='test@example.com',
            subject='Test',
            text_body='Test body',
            html_body=None,
            template_id='test',
        )

        mock_logger.info.assert_called_with(
            'Mailjet dispatched template %s to %s', 'test', 'test@example.com'
        )
