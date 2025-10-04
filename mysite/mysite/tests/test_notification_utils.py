"""Tests for notification utilities following ADR-012"""
from django.test import TestCase
from rest_framework import status

from mysite.notification_utils import (
    create_message,
    success_response,
    error_response,
    validation_error_response,
    rate_limit_response,
)


class NotificationUtilsTestCase(TestCase):
    """Test notification utility functions"""

    def test_create_message_without_context(self):
        """Test creating a message without context"""
        msg = create_message('notifications.profile.updated')
        
        self.assertEqual(msg['i18n_key'], 'notifications.profile.updated')
        self.assertNotIn('context', msg)

    def test_create_message_with_context(self):
        """Test creating a message with context"""
        msg = create_message('errors.file_too_large', {
            'filename': 'photo.jpg',
            'maxSize': '10MB'
        })
        
        self.assertEqual(msg['i18n_key'], 'errors.file_too_large')
        self.assertEqual(msg['context']['filename'], 'photo.jpg')
        self.assertEqual(msg['context']['maxSize'], '10MB')

    def test_success_response_without_messages(self):
        """Test success response without messages"""
        response = success_response({'id': 123})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['id'], 123)
        self.assertNotIn('messages', response.data)

    def test_success_response_with_messages(self):
        """Test success response with messages"""
        response = success_response(
            {'id': 123},
            messages=[create_message('notifications.profile.updated')],
            status_code=status.HTTP_200_OK
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['id'], 123)
        self.assertIn('messages', response.data)
        self.assertEqual(len(response.data['messages']), 1)
        self.assertEqual(
            response.data['messages'][0]['i18n_key'],
            'notifications.profile.updated'
        )

    def test_error_response(self):
        """Test error response format"""
        response = error_response(
            'file_too_large',
            [create_message('errors.file_too_large', {
                'filename': 'photo.jpg',
                'maxSize': '10MB'
            })],
            status.HTTP_400_BAD_REQUEST
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'file_too_large')
        self.assertIn('messages', response.data)
        self.assertEqual(len(response.data['messages']), 1)
        
        msg = response.data['messages'][0]
        self.assertEqual(msg['i18n_key'], 'errors.file_too_large')
        self.assertEqual(msg['context']['filename'], 'photo.jpg')
        self.assertEqual(msg['context']['maxSize'], '10MB')

    def test_validation_error_response(self):
        """Test validation error response with multiple field errors"""
        response = validation_error_response([
            create_message('errors.email_invalid', {'field': 'email'}),
            create_message('errors.password_too_short', {
                'field': 'password',
                'minLength': 8
            })
        ])
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'validation_failed')
        self.assertEqual(len(response.data['messages']), 2)
        
        # Check first error
        self.assertEqual(
            response.data['messages'][0]['i18n_key'],
            'errors.email_invalid'
        )
        self.assertEqual(
            response.data['messages'][0]['context']['field'],
            'email'
        )
        
        # Check second error
        self.assertEqual(
            response.data['messages'][1]['i18n_key'],
            'errors.password_too_short'
        )
        self.assertEqual(
            response.data['messages'][1]['context']['field'],
            'password'
        )
        self.assertEqual(
            response.data['messages'][1]['context']['minLength'],
            8
        )

    def test_rate_limit_response(self):
        """Test rate limit response"""
        response = rate_limit_response('errors.rate_limit', {'retry_after': 60})
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data['error'], 'rate_limit_exceeded')
        self.assertEqual(len(response.data['messages']), 1)
        
        msg = response.data['messages'][0]
        self.assertEqual(msg['i18n_key'], 'errors.rate_limit')
        self.assertEqual(msg['context']['retry_after'], 60)

    def test_rate_limit_response_default(self):
        """Test rate limit response with defaults"""
        response = rate_limit_response()
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data['error'], 'rate_limit_exceeded')
        self.assertEqual(
            response.data['messages'][0]['i18n_key'],
            'errors.rate_limit'
        )

    def test_error_response_no_data_property(self):
        """Test that error responses don't include a 'data' property"""
        response = error_response(
            'test_error',
            [create_message('errors.test')],
            status.HTTP_400_BAD_REQUEST
        )
        
        self.assertNotIn('data', response.data)
        self.assertIn('error', response.data)
        self.assertIn('messages', response.data)

    def test_multiple_messages(self):
        """Test response with multiple messages"""
        messages = [
            create_message('errors.error1'),
            create_message('errors.error2', {'detail': 'info'}),
            create_message('errors.error3', {'count': 5}),
        ]
        
        response = error_response('multiple_errors', messages)
        
        self.assertEqual(len(response.data['messages']), 3)
        self.assertEqual(response.data['messages'][0]['i18n_key'], 'errors.error1')
        self.assertEqual(response.data['messages'][1]['i18n_key'], 'errors.error2')
        self.assertEqual(response.data['messages'][2]['i18n_key'], 'errors.error3')
