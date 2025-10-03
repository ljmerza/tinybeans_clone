"""Tests for the email service layer."""
from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase, override_settings

from emails.mailers import MailerConfigurationError, MailerSendError
from emails.services import clear_registered_templates, email_dispatch_service, register_email_template
from emails.template_loader import load_email_templates
from emails.templates import EMAIL_VERIFICATION_TEMPLATE


class EmailServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        clear_registered_templates()
        mail.outbox = []

        def test_template_renderer(context):
            return (
                f"Subject: {context.get('subject', 'Test')}",
                f"Body: {context.get('message', 'Test message')}",
            )

        register_email_template('test_template', test_template_renderer)

    def tearDown(self) -> None:
        clear_registered_templates()
        load_email_templates()

    def test_register_email_template(self):
        def mock_renderer(context):
            return f"Subject for {context['name']}", f"Body for {context['name']}"

        register_email_template('test_template_2', mock_renderer)

        template = email_dispatch_service.get_template('test_template_2')
        self.assertIsNotNone(template)
        assert template is not None
        self.assertIs(template.renderer, mock_renderer)

    def test_template_replacement(self):
        def renderer1(context):
            return "Subject 1", "Body 1"

        def renderer2(context):
            return "Subject 2", "Body 2"

        register_email_template('test_template_replace', renderer1)
        register_email_template('test_template_replace', renderer2)

        template = email_dispatch_service.get_template('test_template_replace')
        self.assertIsNotNone(template)
        assert template is not None
        self.assertIs(template.renderer, renderer2)

    @patch('emails.services.email_dispatch_service._logger')
    def test_send_email_unknown_template(self, mock_logger):
        dispatched = email_dispatch_service.send_email(
            to_email='test@example.com',
            template_id='unknown_template',
            context={'name': 'Test'},
        )

        self.assertFalse(dispatched)
        mock_logger.error.assert_called_once_with(
            'Unknown email template %s; dropping email', 'unknown_template'
        )
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        MAILJET_ENABLED=False,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_send_email_with_django_backend(self):
        dispatched = email_dispatch_service.send_email(
            to_email='test@example.com',
            template_id='test_template',
            context={'subject': 'Hello John', 'message': 'Welcome, John!'},
        )

        self.assertTrue(dispatched)
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Subject: Hello John')
        self.assertEqual(sent_email.body, 'Body: Welcome, John!')
        self.assertEqual(sent_email.to, ['test@example.com'])

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='test_key',
        MAILJET_API_SECRET='test_secret',
    )
    @patch('emails.services.send_via_mailjet')
    def test_send_email_with_mailjet(self, mock_mailjet):
        mock_mailjet.return_value = None

        dispatched = email_dispatch_service.send_email(
            to_email='user@example.com',
            template_id='test_template',
            context={'subject': 'Update', 'message': 'You have updates!'},
        )

        self.assertTrue(dispatched)
        mock_mailjet.assert_called_once_with(
            to_email='user@example.com',
            subject='Subject: Update',
            text_body='Body: You have updates!',
            html_body=None,
            template_id='test_template',
        )
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='test_key',
        MAILJET_API_SECRET='test_secret',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    @patch('emails.services.send_via_mailjet')
    def test_send_email_mailjet_config_error_fallback(self, mock_mailjet):
        mock_mailjet.side_effect = MailerConfigurationError('Mailjet not configured')

        dispatched = email_dispatch_service.send_email(
            to_email='user@example.com',
            template_id='test_template',
            context={'subject': 'Test', 'message': 'Test Body'},
        )

        self.assertTrue(dispatched)
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Subject: Test')
        self.assertEqual(sent_email.body, 'Body: Test Body')

    @override_settings(
        MAILJET_ENABLED=True,
        MAILJET_API_KEY='test_key',
        MAILJET_API_SECRET='test_secret',
    )
    @patch('emails.services.send_via_mailjet')
    @patch('emails.services.logger')
    def test_send_email_mailjet_send_error(self, mock_logger, mock_mailjet):
        mock_mailjet.side_effect = MailerSendError('HTTP 500')

        with self.assertRaises(MailerSendError):
            email_dispatch_service.send_email(
                to_email='user@example.com',
                template_id='test_template',
                context={'subject': 'Test', 'message': 'Test Body'},
            )

        self.assertGreaterEqual(mock_logger.warning.call_count, 1)

    @override_settings(
        MAILJET_ENABLED=False,
        DEFAULT_FROM_EMAIL='test@example.com',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    @patch('emails.services.email_dispatch_service._logger')
    def test_send_email_success_logging(self, mock_logger):
        email_dispatch_service.send_email(
            to_email='user@example.com',
            template_id='test_template',
            context={'subject': 'Test', 'message': 'Test Body'},
        )

        mock_logger.info.assert_called_with(
            'Dispatched %s email to %s', 'test_template', 'user@example.com'
        )

    @override_settings(
        MAILJET_ENABLED=False,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@example.com',
    )
    @patch('emails.services.send_mail')
    @patch('emails.services.logger')
    def test_send_email_django_send_error(self, mock_logger, mock_send_mail):
        mock_send_mail.side_effect = Exception('SMTP Error')

        with self.assertRaises(Exception):
            email_dispatch_service.send_email(
                to_email='user@example.com',
                template_id='test_template',
                context={'subject': 'Test', 'message': 'Test Body'},
            )

        mock_logger.warning.assert_called()


class EmailTemplateLoaderTests(SimpleTestCase):
    def tearDown(self) -> None:
        clear_registered_templates()
        load_email_templates()

    def test_file_template_renders_subject_text_html(self):
        clear_registered_templates()
        load_email_templates()

        template = email_dispatch_service.get_template(EMAIL_VERIFICATION_TEMPLATE)
        self.assertIsNotNone(template)
        assert template is not None

        rendered = template.render({'token': '123456', 'verification_link': 'https://example.com/verify'})

        self.assertEqual(rendered.subject, 'Verify your Tinybeans-inspired account')
        self.assertIn('123456', rendered.text_body)
        self.assertIn('https://example.com/verify', rendered.text_body)
        self.assertIsNotNone(rendered.html_body)
        assert rendered.html_body is not None
        self.assertIn('<html>', rendered.html_body)
        self.assertIn('123456', rendered.html_body)

    @override_settings(
        MAILJET_ENABLED=False,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@example.com',
    )
    def test_file_template_sends_multipart_email(self):
        clear_registered_templates()
        load_email_templates()
        mail.outbox = []

        dispatched = email_dispatch_service.send_email(
            to_email='recipient@example.com',
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={'token': '654321', 'verification_link': 'https://example.com/verify'},
        )

        self.assertTrue(dispatched)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Verify your Tinybeans-inspired account')
        self.assertEqual(
            message.body.splitlines(),
            [
                'Hi there,',
                '',
                'Thanks for signing up! Please use the code below to verify your email address:',
                'Verification link: https://example.com/verify',
                '654321',
                '',
                'Enter this code in the app to activate your account. If you did not create an account, you can ignore this email.',
            ],
        )
        self.assertEqual(len(message.alternatives), 1)
        html_content, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('654321', html_content)
