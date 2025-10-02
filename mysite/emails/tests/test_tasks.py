"""Tests for emailing tasks and template system."""
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from django.core import mail

from emails.tasks import register_email_template, send_email_task, _TEMPLATE_REGISTRY
from emails.mailers import MailerConfigurationError, MailerSendError, send_via_mailjet


class EmailTaskTests(TestCase):
    def setUp(self):
        # Clear any existing templates to avoid interference
        _TEMPLATE_REGISTRY.clear()
        # Clear django mail outbox
        mail.outbox = []
        
        # Register a test template for testing
        def test_template_renderer(context):
            return f"Subject: {context.get('subject', 'Test')}", f"Body: {context.get('message', 'Test message')}"
        register_email_template('test_template', test_template_renderer)

    def tearDown(self):
        _TEMPLATE_REGISTRY.clear()

    def test_register_email_template(self):
        """Test registering an email template."""
        def mock_renderer(context):
            return f"Subject for {context['name']}", f"Body for {context['name']}"
        
        register_email_template('test_template_2', mock_renderer)
        
        self.assertIn('test_template_2', _TEMPLATE_REGISTRY)
        self.assertEqual(_TEMPLATE_REGISTRY['test_template_2'], mock_renderer)

    def test_template_replacement(self):
        """Test that registering a template with the same ID replaces the old one."""
        def renderer1(context):
            return "Subject 1", "Body 1"
        
        def renderer2(context):
            return "Subject 2", "Body 2"
        
        register_email_template('test_template_replace', renderer1)
        register_email_template('test_template_replace', renderer2)
        
        self.assertEqual(_TEMPLATE_REGISTRY['test_template_replace'], renderer2)

    @patch('emails.tasks.logger')
    def test_send_email_task_unknown_template(self, mock_logger):
        """Test sending email with unknown template logs error and returns early."""
        result = send_email_task.run(
            to_email='test@example.com',
            template_id='unknown_template',
            context={'name': 'Test'}
        )
        
        mock_logger.error.assert_called_once_with(
            'Unknown email template %s; dropping email', 'unknown_template'
        )
        # Should not send any emails
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        MAILJET_ENABLED=False,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_send_email_task_with_django_backend(self):
        """Test sending email using Django's email backend."""
        send_email_task.run(
            to_email='test@example.com',
            template_id='test_template',
            context={'subject': 'Hello John', 'message': 'Welcome, John!'}
        )
        
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Subject: Hello John')
        self.assertEqual(sent_email.body, 'Body: Welcome, John!')
        self.assertEqual(sent_email.to, ['test@example.com'])

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='test_key',
        MAILJET_API_SECRET='test_secret'
    )
    @patch('emails.mailers.send_via_mailjet')
    def test_send_email_task_with_mailjet(self, mock_mailjet):
        """Test sending email using Mailjet when enabled."""
        mock_mailjet.return_value = None
        
        send_email_task.run(
            to_email='user@example.com',
            template_id='test_template',
            context={'subject': 'Update', 'message': 'You have updates!'}
        )
        
        mock_mailjet.assert_called_once_with(
            to_email='user@example.com',
            subject='Subject: Update',
            body='Body: You have updates!',
            template_id='test_template'
        )
        # Should not fallback to Django mail
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='test_key',
        MAILJET_API_SECRET='test_secret',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    @patch('emails.mailers.send_via_mailjet')
    def test_send_email_task_mailjet_config_error_fallback(self, mock_mailjet):
        """Test fallback to Django mail when Mailjet is misconfigured."""
        mock_mailjet.side_effect = MailerConfigurationError("Mailjet not configured")
        
        send_email_task.run(
            to_email='user@example.com',
            template_id='test_template',
            context={'subject': 'Test', 'message': 'Test Body'}
        )
        
        # Should fallback to Django mail
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Subject: Test')
        self.assertEqual(sent_email.body, 'Body: Test Body')

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='test_key',
        MAILJET_API_SECRET='test_secret'
    )
    @patch('emails.mailers.send_via_mailjet')
    @patch('emails.tasks.logger')
    def test_send_email_task_mailjet_send_error(self, mock_logger, mock_mailjet):
        """Test handling Mailjet send errors."""
        mock_mailjet.side_effect = MailerSendError("HTTP 500")
        
        with self.assertRaises(MailerSendError):
            send_email_task.run(
                to_email='user@example.com',
                template_id='test_template',
                context={'subject': 'Test', 'message': 'Test Body'}
            )
        
        # Logger should be called twice - once for Mailjet error, once for task error
        self.assertGreaterEqual(mock_logger.warning.call_count, 1)

    @override_settings(
        MAILJET_ENABLED=False,
        DEFAULT_FROM_EMAIL='test@example.com',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    @patch('emails.tasks.logger')
    def test_send_email_task_success_logging(self, mock_logger):
        """Test success logging for email sending."""
        send_email_task.run(
            to_email='user@example.com',
            template_id='test_template',
            context={'subject': 'Test', 'message': 'Test Body'}
        )
        
        mock_logger.info.assert_called_with(
            'Dispatched %s email to %s', 'test_template', 'user@example.com'
        )

    @override_settings(
        MAILJET_ENABLED=False,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@example.com'
    )
    @patch('emails.tasks.send_mail')
    @patch('emails.tasks.logger')
    def test_send_email_task_django_send_error(self, mock_logger, mock_send_mail):
        """Test handling Django email send errors."""
        mock_send_mail.side_effect = Exception("SMTP Error")
        
        with self.assertRaises(Exception):
            send_email_task.run(
                to_email='user@example.com',
                template_id='test_template',
                context={'subject': 'Test', 'message': 'Test Body'}
            )
        
        mock_logger.warning.assert_called()


class MailjetMailerErrorTests(TestCase):
    """Additional tests for Mailjet mailer error conditions."""
    
    @override_settings(MAILJET_ENABLED=False)
    def test_mailjet_disabled_raises_configuration_error(self):
        """Test that using Mailjet when disabled raises configuration error."""
        with self.assertRaises(MailerConfigurationError) as cm:
            send_via_mailjet(
                to_email='test@example.com',
                subject='Test',
                body='Test body',
                template_id='test'
            )
        
        self.assertIn('not configured', str(cm.exception))

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='key',
        MAILJET_API_SECRET='secret',
        MAILJET_FROM_EMAIL='sender@example.com',
        MAILJET_FROM_NAME='Test Sender',
        MAILJET_USE_SANDBOX=True,
        MAILJET_API_URL='https://api.mailjet.com/v3.1/send'
    )
    @patch('emails.mailers.requests.post')
    def test_mailjet_request_exception(self, mock_post):
        """Test handling of requests exceptions in Mailjet."""
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")
        
        with self.assertRaises(MailerSendError) as cm:
            send_via_mailjet(
                to_email='test@example.com',
                subject='Test',
                body='Test body',
                template_id='test'
            )
        
        self.assertIn('Connection error', str(cm.exception))

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='key',
        MAILJET_API_SECRET='secret',
        MAILJET_FROM_EMAIL='sender@example.com',
        MAILJET_FROM_NAME='Test Sender',
        MAILJET_USE_SANDBOX=False,
        MAILJET_API_URL='https://api.mailjet.com/v3.1/send'
    )
    @patch('emails.mailers.requests.post')
    def test_mailjet_http_error_response(self, mock_post):
        """Test handling of HTTP error responses from Mailjet."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        with self.assertRaises(MailerSendError) as cm:
            send_via_mailjet(
                to_email='test@example.com',
                subject='Test',
                body='Test body',
                template_id='test'
            )
        
        self.assertIn('HTTP 400', str(cm.exception))

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='key',
        MAILJET_API_SECRET='secret',
        MAILJET_FROM_EMAIL='sender@example.com',
        MAILJET_FROM_NAME='Test Sender',
        MAILJET_USE_SANDBOX=False,
        MAILJET_API_URL='https://api.mailjet.com/v3.1/send'
    )
    @patch('emails.mailers.requests.post')
    @patch('emails.mailers.logger')
    def test_mailjet_success_response(self, mock_logger, mock_post):
        """Test successful Mailjet response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Messages': [{'Status': 'success'}]
        }
        mock_post.return_value = mock_response
        
        # Should not raise an exception
        send_via_mailjet(
            to_email='test@example.com',
            subject='Test',
            body='Test body',
            template_id='test'
        )
        
        mock_logger.info.assert_called_with(
            'Mailjet dispatched template %s to %s', 'test', 'test@example.com'
        )