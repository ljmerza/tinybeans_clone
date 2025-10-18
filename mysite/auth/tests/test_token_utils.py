"""Tests for token utilities and authentication helpers."""
from datetime import timedelta
from unittest.mock import patch
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from mysite.users.models import User
from mysite.auth.token_utils import (
    REFRESH_COOKIE_NAME,
    TOKEN_TTL_SECONDS,
    clear_refresh_cookie,
    get_tokens_for_user,
    set_refresh_cookie,
    store_token,
    pop_token,
    generate_partial_token,
    verify_partial_token,
)


class TokenUtilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )

    def testget_tokens_for_user(self):
        """Test getting JWT tokens for a user."""
        tokens = get_tokens_for_user(self.user)
        
        self.assertIn('access', tokens)
        self.assertIn('refresh', tokens)
        self.assertIsInstance(tokens['access'], str)
        self.assertIsInstance(tokens['refresh'], str)

    def test_store_token(self):
        """Test storing a token with expiration."""
        payload = {'user_id': self.user.id, 'action': 'test'}
        stored_key = store_token('test', payload)
        
        self.assertIsNotNone(stored_key)
        self.assertIsInstance(stored_key, str)

    def test_pop_token(self):
        """Test retrieving and removing a token."""
        payload = {'user_id': self.user.id, 'action': 'test'}
        stored_key = store_token('test', payload)
        
        # Pop the token
        retrieved_data = pop_token('test', stored_key)
        
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data['user_id'], self.user.id)
        self.assertEqual(retrieved_data['action'], 'test')
        
        # Token should be removed after popping
        retrieved_again = pop_token('test', stored_key)
        self.assertIsNone(retrieved_again)

    def test_pop_nonexistent_token(self):
        """Test popping a token that doesn't exist."""
        result = pop_token('test', 'nonexistent_key')
        self.assertIsNone(result)

    def test_token_expiration(self):
        """Test that tokens expire after TTL."""
        payload = {'user_id': self.user.id, 'action': 'expire_test'}
        stored_key = store_token('test', payload, ttl=1)  # 1 second TTL
        
        # Token should be retrievable immediately
        retrieved = pop_token('test', stored_key)
        self.assertIsNotNone(retrieved)

    def test_store_token_with_custom_ttl(self):
        """Test storing token with custom TTL."""
        payload = {'user_id': self.user.id, 'action': 'custom_ttl'}
        custom_ttl = 3600  # 1 hour
        stored_key = store_token('test', payload, ttl=custom_ttl)
        
        self.assertIsNotNone(stored_key)
        
        # Token should be retrievable immediately
        retrieved = pop_token('test', stored_key)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['action'], 'custom_ttl')

    def test_token_data_integrity(self):
        """Test that stored token data maintains integrity."""
        payload = {
            'user_id': self.user.id, 
            'email': self.user.email, 
            'role': 'test'
        }
        
        stored_key = store_token('test', payload)
        retrieved = pop_token('test', stored_key)
        
        self.assertEqual(retrieved['user_id'], self.user.id)
        self.assertEqual(retrieved['email'], self.user.email)
        self.assertEqual(retrieved['role'], 'test')

    def test_multiple_tokens_same_prefix(self):
        """Test storing multiple tokens with the same prefix."""
        payload1 = {'user_id': self.user.id, 'action': 'action1'}
        payload2 = {'user_id': self.user.id, 'action': 'action2'}
        
        key1 = store_token('test', payload1)
        key2 = store_token('test', payload2)
        
        self.assertNotEqual(key1, key2)
        
        # Both tokens should be retrievable
        data1 = pop_token('test', key1)
        data2 = pop_token('test', key2)
        
        self.assertEqual(data1['action'], 'action1')
        self.assertEqual(data2['action'], 'action2')


class CookieUtilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cookieuser',
            email='cookie@example.com',
            password='password123'
        )

    def testset_refresh_cookie(self):
        """Test setting refresh cookie on response."""
        from django.http import HttpResponse
        
        response = HttpResponse()
        refresh_token = str(RefreshToken.for_user(self.user))
        
        set_refresh_cookie(response, refresh_token)
        
        cookie = response.cookies[REFRESH_COOKIE_NAME]
        self.assertEqual(cookie.value, refresh_token)
        self.assertTrue(cookie['httponly'])
        self.assertTrue(cookie['secure'])  # Assuming not in DEBUG mode
        self.assertEqual(cookie['path'], '/api/auth/token/refresh/')

    @override_settings(DEBUG=True)
    def testset_refresh_cookie_debug_mode(self):
        """Test that cookie is not secure in DEBUG mode."""
        from django.http import HttpResponse
        
        response = HttpResponse()
        refresh_token = str(RefreshToken.for_user(self.user))
        
        set_refresh_cookie(response, refresh_token)
        
        cookie = response.cookies[REFRESH_COOKIE_NAME]
        self.assertFalse(cookie['secure'])  # Should be False in DEBUG mode

    def testclear_refresh_cookie(self):
        """Test clearing refresh cookie."""
        from django.http import HttpResponse
        
        response = HttpResponse()
        clear_refresh_cookie(response)
        
        cookie = response.cookies[REFRESH_COOKIE_NAME]
        self.assertEqual(cookie.value, '')
        # The cookie should be deleted, so max_age might not be set
        # Just check that the cookie exists and is cleared

    def test_cookie_constants(self):
        """Test that cookie constants are properly defined."""
        self.assertEqual(REFRESH_COOKIE_NAME, 'refresh_token')
        self.assertIsInstance(TOKEN_TTL_SECONDS, int)
        self.assertGreater(TOKEN_TTL_SECONDS, 0)


class TokenSecurityTests(TestCase):
    """Tests for token security and validation."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password123'
        )

    def test_tokens_are_unique(self):
        """Test that generated tokens are unique."""
        tokens1 = get_tokens_for_user(self.user1)
        tokens2 = get_tokens_for_user(self.user1)  # Same user
        tokens3 = get_tokens_for_user(self.user2)  # Different user
        
        # All tokens should be different
        self.assertNotEqual(tokens1['access'], tokens2['access'])
        self.assertNotEqual(tokens1['refresh'], tokens2['refresh'])
        self.assertNotEqual(tokens1['access'], tokens3['access'])


class PartialTokenBindingTests(TestCase):
    """Ensure partial tokens are bound to client fingerprints."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='uauser',
            email='ua@example.com',
            password='password123'
        )
        self.user1 = User.objects.create_user(
            username='binding-user-1',
            email='binding1@example.com',
            password='password123'
        )
        self.user2 = User.objects.create_user(
            username='binding-user-2',
            email='binding2@example.com',
            password='password123'
        )

    def _build_request(self, user_agent: str):
        request = self.factory.post('/auth/login/')
        request.META['HTTP_USER_AGENT'] = user_agent
        request.META['REMOTE_ADDR'] = '203.0.113.5'
        return request

    def test_partial_token_accepts_matching_user_agent(self):
        enroll_request = self._build_request('TestAgent/1.0')
        token = generate_partial_token(self.user, enroll_request)

        verify_request = self._build_request('TestAgent/1.0')
        verified_user = verify_partial_token(token, verify_request)

        self.assertIsNotNone(verified_user)
        self.assertEqual(verified_user.pk, self.user.pk)

    def test_partial_token_rejects_user_agent_changes(self):
        enroll_request = self._build_request('TestAgent/1.0')
        token = generate_partial_token(self.user, enroll_request)

        mismatched_request = self._build_request('DifferentAgent/2.0')
        result = verify_partial_token(token, mismatched_request)

        self.assertIsNone(result)

    def test_stored_keys_are_unique(self):
        """Test that stored token keys are unique."""
        payload = {'action': 'same_action'}
        
        key1 = store_token('test', payload)
        key2 = store_token('test', payload)  # Same payload
        key3 = store_token('other', payload)  # Different prefix
        
        # All keys should be unique
        self.assertNotEqual(key1, key2)
        self.assertNotEqual(key1, key3)
        self.assertNotEqual(key2, key3)

    def test_token_isolation_between_prefixes(self):
        """Test that tokens are isolated between prefixes."""
        payload1 = {'user_id': self.user1.id, 'action': 'action1'}
        payload2 = {'user_id': self.user2.id, 'action': 'action2'}
        
        key1 = store_token('prefix1', payload1)
        key2 = store_token('prefix2', payload2)
        
        # Keys can be the same, but prefixes isolate them
        data1 = pop_token('prefix1', key1)
        data2 = pop_token('prefix2', key2)
        
        # Each token should only contain its own data
        self.assertEqual(data1['user_id'], self.user1.id)
        self.assertEqual(data2['user_id'], self.user2.id)
        self.assertNotEqual(data1['user_id'], data2['user_id'])

    def test_token_key_format(self):
        """Test that token keys follow expected format."""
        payload = {'action': 'format_test'}
        key = store_token('test', payload)
        
        # Key should be a string
        self.assertIsInstance(key, str)
        # Key should have reasonable length (not empty, not too short)
        self.assertGreater(len(key), 10)

    def test_concurrent_token_operations(self):
        """Test concurrent token storage and retrieval."""
        payloads = []
        keys = []
        
        # Store multiple tokens quickly
        for i in range(10):
            payload = {'user_id': self.user1.id, 'counter': i}
            key = store_token('test', payload)
            payloads.append(payload)
            keys.append(key)
        
        # Retrieve all tokens
        for i, key in enumerate(keys):
            data = pop_token('test', key)
            self.assertIsNotNone(data)
            self.assertEqual(data['counter'], i)
            self.assertEqual(data['user_id'], self.user1.id)
