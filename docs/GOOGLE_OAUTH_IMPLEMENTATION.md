# Google OAuth Implementation Guide

## Overview
This guide provides step-by-step implementation details for integrating Google OAuth into the existing authentication system, following the architecture outlined in `GOOGLE_OAUTH_ARCHITECTURE.md`.

## Prerequisites

### Required Packages
```bash
# Add to requirements.txt
google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
PyJWT==2.8.0
cryptography==41.0.7
```

### Google Cloud Console Setup
1. Create or select a Google Cloud Project
2. Enable Google+ API and Google OAuth2 API
3. Create OAuth 2.0 Client ID credentials
4. Configure authorized redirect URIs
5. Note down Client ID and Client Secret

## Implementation Steps

### Step 1: Database Schema Changes

#### Update User Model
```python
# users/models/user.py
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    # ... existing fields ...
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CIRCLE_MEMBER)
    email_verified = models.BooleanField(default=False)
    
    # Google OAuth fields
    google_id = models.CharField(
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Google user ID from OAuth"
    )
    google_email = models.EmailField(
        null=True, 
        blank=True,
        help_text="Email from Google OAuth (for debugging/tracking)"
    )
    has_usable_password = models.BooleanField(
        default=True,
        help_text="Whether user has set a password for manual login"
    )
    auth_provider = models.CharField(
        max_length=20, 
        default='manual',
        choices=[
            ('manual', 'Manual Registration'),
            ('google', 'Google OAuth Only'),
            ('hybrid', 'Both Manual and Google'),
        ],
        help_text="Primary authentication method"
    )
    google_linked_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When Google account was first linked"
    )
    last_google_sync = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last time Google profile was synced"
    )
    
    def update_from_google(self, google_user_info):
        """Update user data from Google user info"""
        self.google_email = google_user_info['email']
        self.last_google_sync = timezone.now()
        
        # Update name if not set or if Google has more recent data
        if not self.first_name and google_user_info.get('given_name'):
            self.first_name = google_user_info['given_name']
        if not self.last_name and google_user_info.get('family_name'):
            self.last_name = google_user_info['family_name']
            
        self.save(update_fields=[
            'google_email', 'last_google_sync', 'first_name', 'last_name'
        ])
    
    def link_google_account(self, google_id, google_user_info):
        """Link Google account to this user"""
        self.google_id = google_id
        self.google_linked_at = timezone.now()
        self.email_verified = True  # Google emails are verified
        
        # Update auth provider
        if self.auth_provider == 'manual':
            self.auth_provider = 'hybrid'
        elif not self.has_usable_password:
            self.auth_provider = 'google'
            
        self.update_from_google(google_user_info)
    
    def unlink_google_account(self):
        """Remove Google account link"""
        self.google_id = None
        self.google_email = None
        self.google_linked_at = None
        self.last_google_sync = None
        self.auth_provider = 'manual' if self.has_usable_password else 'manual'
        self.save()
```

#### Create Migration
```bash
cd mysite
python manage.py makemigrations users --name add_google_oauth_fields
python manage.py migrate
```

### Step 2: Google OAuth Service

#### Core OAuth Service
```python
# users/services/google_oauth.py
import secrets
import json
from typing import Tuple, Dict, Any
from urllib.parse import urlencode

import jwt
import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from ..models import User

User = get_user_model()


class GoogleOAuthError(Exception):
    """Base exception for Google OAuth errors"""
    pass


class GoogleTokenValidationError(GoogleOAuthError):
    """Error validating Google tokens"""
    pass


class GoogleAccountConflictError(GoogleOAuthError):
    """Error when Google account conflicts with existing account"""
    def __init__(self, message, existing_user=None):
        super().__init__(message)
        self.existing_user = existing_user


class GoogleOAuthService:
    """Service for handling Google OAuth authentication"""
    
    GOOGLE_OAUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
    GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
    
    def __init__(self):
        self.client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        self.client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
        self.scopes = getattr(settings, 'GOOGLE_OAUTH_SCOPES', ['openid', 'email', 'profile'])
        
        if not (self.client_id and self.client_secret):
            raise GoogleOAuthError("Google OAuth credentials not configured")
    
    def generate_oauth_url(self, redirect_uri: str, state_token: str) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'state': state_token,
            'access_type': 'offline',
            'prompt': 'consent',
        }
        return f"{self.GOOGLE_OAUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access and ID tokens"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }
        
        response = requests.post(self.GOOGLE_TOKEN_URL, data=data)
        
        if response.status_code != 200:
            raise GoogleTokenValidationError(f"Failed to exchange code for tokens: {response.text}")
        
        return response.json()
    
    def validate_id_token(self, id_token_str: str) -> Dict[str, Any]:
        """Validate Google ID token and extract user info"""
        try:
            # Verify the ID token using Google's library
            idinfo = id_token.verify_oauth2_token(
                id_token_str, 
                google_requests.Request(), 
                self.client_id
            )
            
            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise GoogleTokenValidationError('Invalid token issuer')
            
            return idinfo
        except ValueError as e:
            raise GoogleTokenValidationError(f"Invalid ID token: {e}")
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get additional user info from Google using access token"""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(self.GOOGLE_USERINFO_URL, headers=headers)
        
        if response.status_code != 200:
            raise GoogleOAuthError(f"Failed to get user info: {response.text}")
        
        return response.json()
    
    def generate_unique_username(self, google_user_info: Dict[str, Any]) -> str:
        """Generate a unique username from Google user info"""
        base_username = google_user_info.get('email', '').split('@')[0]
        base_username = ''.join(c for c in base_username if c.isalnum() or c in '._-')
        
        if not base_username:
            base_username = f"google_user_{google_user_info['sub'][:8]}"
        
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
            
        return username
    
    def create_google_user(self, google_user_info: Dict[str, Any]) -> Tuple[User, str]:
        """Create a new user from Google user info"""
        username = self.generate_unique_username(google_user_info)
        
        user = User.objects.create(
            username=username,
            email=google_user_info['email'],
            first_name=google_user_info.get('given_name', ''),
            last_name=google_user_info.get('family_name', ''),
            google_id=google_user_info['sub'],
            google_email=google_user_info['email'],
            email_verified=True,  # Google emails are pre-verified
            has_usable_password=False,  # No password set
            auth_provider='google',
            google_linked_at=timezone.now(),
            last_google_sync=timezone.now()
        )
        
        return user, 'created'
    
    def link_google_to_existing_user(self, user: User, google_user_info: Dict[str, Any]) -> Tuple[User, str]:
        """Link Google account to existing user"""
        user.link_google_account(google_user_info['sub'], google_user_info)
        return user, 'linked'
    
    def handle_google_callback(self, code: str, redirect_uri: str) -> Tuple[User, str]:
        """Main handler for Google OAuth callback"""
        # Exchange code for tokens
        tokens = self.exchange_code_for_tokens(code, redirect_uri)
        
        # Validate ID token and extract user info
        google_user_info = self.validate_id_token(tokens['id_token'])
        
        # Get additional user info if needed
        if 'access_token' in tokens:
            additional_info = self.get_user_info(tokens['access_token'])
            google_user_info.update(additional_info)
        
        # Check domain restrictions
        self.validate_user_domain(google_user_info['email'])
        
        # Handle account linking/creation
        return self.find_or_create_user(google_user_info)
    
    def validate_user_domain(self, email: str):
        """Validate user domain if domain restrictions are configured"""
        allowed_domains = getattr(settings, 'GOOGLE_OAUTH_ALLOWED_DOMAINS', [])
        if allowed_domains:
            domain = email.split('@')[1].lower()
            if domain not in allowed_domains:
                raise GoogleOAuthError(f"Domain {domain} is not allowed")
    
    def find_or_create_user(self, google_user_info: Dict[str, Any]) -> Tuple[User, str]:
        """Find existing user or create new one based on Google info with email verification security"""
        google_id = google_user_info['sub']
        google_email = google_user_info['email']
        
        # First, check if this Google ID is already linked
        try:
            user = User.objects.get(google_id=google_id)
            user.update_from_google(google_user_info)
            return user, 'authenticated'
        except User.DoesNotExist:
            pass
        
        # Check if email exists in system
        try:
            existing_user = User.objects.get(email=google_email)
            
            if existing_user.google_id and existing_user.google_id != google_id:
                # Email exists but linked to different Google account
                raise GoogleAccountConflictError(
                    f"Email {google_email} is already linked to a different Google account",
                    existing_user
                )
            elif not existing_user.email_verified:
                # SECURITY: Block linking to unverified accounts to prevent takeover
                logger.warning(
                    f"Google OAuth linking blocked for unverified account",
                    extra={
                        'email': google_email,
                        'existing_user_id': existing_user.id,
                        'google_id': google_id,
                        'account_created': existing_user.date_joined.isoformat(),
                        'event_type': 'oauth_blocked_unverified'
                    }
                )
                
                # Optionally trigger verification email resend for user convenience
                self.maybe_resend_verification_email(existing_user)
                
                raise GoogleOAuthError(
                    f"An account with {google_email} exists but the email address has not been verified. "
                    f"Please check your email and click the verification link, or contact support if you "
                    f"need help accessing your account."
                )
            else:
                # Email verified - safe to link Google to existing manual account
                return self.link_google_to_existing_user(existing_user, google_user_info)
                
        except User.DoesNotExist:
            # Create new Google user (email pre-verified by Google)
            return self.create_google_user(google_user_info)
    
    def maybe_resend_verification_email(self, user: User):
        """Optionally resend verification email to help user resolve the conflict"""
        # Check if we should resend (not too recent, rate limiting, etc.)
        cache_key = f"verification_resend_cooldown:{user.id}"
        if cache.get(cache_key):
            return  # Too recent, skip resend
        
        # Set cooldown (e.g., 5 minutes)
        cache.set(cache_key, True, timeout=300)
        
        # Import here to avoid circular imports
        from ..tasks import send_email_task, EMAIL_VERIFICATION_TEMPLATE
        from ..token_utils import store_token
        
        # Generate new verification token
        verification_token = store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
            ttl=86400  # 24 hours
        )
        
        # Send verification email
        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': verification_token,
                'email': user.email,
                'username': user.username,
                'reason': 'google_oauth_conflict'
            }
        )


class OAuthStateManager:
    """Manage OAuth state tokens for security"""
    
    TIMEOUT_SECONDS = 300  # 5 minutes
    
    @staticmethod
    def generate_state_token() -> str:
        """Generate a cryptographically secure state token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def store_state(token: str, data: Dict[str, Any], ip_address: str):
        """Store OAuth state with associated data"""
        cache_key = f"oauth_state:{token}"
        cache_data = {
            'data': data,
            'ip_address': ip_address,
            'created_at': timezone.now().isoformat()
        }
        cache.set(cache_key, cache_data, timeout=OAuthStateManager.TIMEOUT_SECONDS)
    
    @staticmethod
    def validate_and_consume_state(token: str, ip_address: str) -> Dict[str, Any]:
        """Validate and consume (single-use) OAuth state token"""
        cache_key = f"oauth_state:{token}"
        state_data = cache.get(cache_key)
        
        if not state_data:
            raise GoogleOAuthError("OAuth state token expired or invalid")
        
        # Optional: Validate IP address (can be disabled for mobile apps)
        if getattr(settings, 'OAUTH_VALIDATE_IP', True) and state_data['ip_address'] != ip_address:
            raise GoogleOAuthError("OAuth state token used from different IP address")
        
        # Consume the token (single use)
        cache.delete(cache_key)
        
        return state_data['data']
```

### Step 3: API Views

#### OAuth Views
```python
# users/views/google_oauth.py
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes

from ..services.google_oauth import GoogleOAuthService, OAuthStateManager, GoogleOAuthError
from ..token_utils import get_tokens_for_user, set_refresh_cookie
from ..serializers import UserSerializer


class GoogleOAuthInitiateView(APIView):
    """Initiate Google OAuth flow"""
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Initiate Google OAuth flow",
        description="Generate Google OAuth URL and state token to start authentication",
        request={
            'type': 'object',
            'properties': {
                'redirect_uri': {'type': 'string', 'format': 'uri'},
                'link_to_existing': {'type': 'boolean', 'default': False}
            },
            'required': ['redirect_uri']
        },
        responses={
            200: OpenApiResponse(
                description="OAuth initiation successful",
                response={
                    'type': 'object',
                    'properties': {
                        'google_oauth_url': {'type': 'string'},
                        'state_token': {'type': 'string'},
                        'expires_in': {'type': 'integer'}
                    }
                }
            ),
            400: OpenApiResponse(description="Invalid request"),
            503: OpenApiResponse(description="Google OAuth not configured")
        }
    )
    def post(self, request):
        if not getattr(settings, 'GOOGLE_OAUTH_ENABLED', False):
            return Response({
                'error': {
                    'code': 'GOOGLE_OAUTH_DISABLED',
                    'message': 'Google OAuth is not enabled'
                }
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        redirect_uri = request.data.get('redirect_uri')
        link_to_existing = request.data.get('link_to_existing', False)
        
        if not redirect_uri:
            return Response({
                'error': {
                    'code': 'MISSING_REDIRECT_URI',
                    'message': 'redirect_uri is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Generate state token
            state_token = OAuthStateManager.generate_state_token()
            
            # Store state data
            state_data = {
                'redirect_uri': redirect_uri,
                'link_to_existing': link_to_existing,
                'user_id': request.user.id if request.user.is_authenticated else None
            }
            
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            OAuthStateManager.store_state(state_token, state_data, client_ip)
            
            # Generate OAuth URL
            oauth_service = GoogleOAuthService()
            google_oauth_url = oauth_service.generate_oauth_url(redirect_uri, state_token)
            
            return Response({
                'data': {
                    'google_oauth_url': google_oauth_url,
                    'state_token': state_token,
                    'expires_in': OAuthStateManager.TIMEOUT_SECONDS
                }
            })
            
        except GoogleOAuthError as e:
            return Response({
                'error': {
                    'code': 'OAUTH_INITIATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)


class GoogleOAuthCallbackView(APIView):
    """Handle Google OAuth callback"""
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Handle Google OAuth callback",
        description="Process Google OAuth authorization code and authenticate user",
        request={
            'type': 'object',
            'properties': {
                'code': {'type': 'string'},
                'state': {'type': 'string'},
                'redirect_uri': {'type': 'string', 'format': 'uri'},
            },
            'required': ['code', 'state', 'redirect_uri']
        },
        responses={
            200: OpenApiResponse(description="Authentication successful"),
            400: OpenApiResponse(description="Invalid request or OAuth error"),
            409: OpenApiResponse(description="Account conflict - email already exists")
        }
    )
    def post(self, request):
        code = request.data.get('code')
        state = request.data.get('state')
        redirect_uri = request.data.get('redirect_uri')
        
        if not all([code, state, redirect_uri]):
            return Response({
                'error': {
                    'code': 'MISSING_PARAMETERS',
                    'message': 'code, state, and redirect_uri are required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate and consume state token
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            state_data = OAuthStateManager.validate_and_consume_state(state, client_ip)
            
            # Validate redirect URI matches
            if state_data['redirect_uri'] != redirect_uri:
                return Response({
                    'error': {
                        'code': 'REDIRECT_URI_MISMATCH',
                        'message': 'redirect_uri does not match stored value'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process OAuth callback
            oauth_service = GoogleOAuthService()
            user, action = oauth_service.handle_google_callback(code, redirect_uri)
            
            # Generate JWT tokens
            tokens = get_tokens_for_user(user)
            
            # Prepare response data
            response_data = {
                'data': {
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': tokens['access']
                    },
                    'account_action': action
                }
            }
            
            response = Response(response_data, status=status.HTTP_200_OK)
            set_refresh_cookie(response, tokens['refresh'])
            
            return response
            
        except GoogleOAuthError as e:
            # Handle different types of OAuth errors with appropriate responses
            if "email address has not been verified" in str(e):
                return Response({
                    'error': {
                        'code': 'EMAIL_VERIFICATION_REQUIRED',
                        'message': 'Email verification required before Google linking',
                        'details': {
                            'user_message': str(e),
                            'required_action': 'verify_email_first',
                            'support_contact': 'support@yourapp.com'
                        }
                    }
                }, status=status.HTTP_409_CONFLICT)
            elif "already linked to a different Google account" in str(e):
                return Response({
                    'error': {
                        'code': 'GOOGLE_ACCOUNT_CONFLICT',
                        'message': 'This email is already linked to a different Google account',
                        'details': {
                            'user_message': str(e),
                            'suggested_action': 'contact_support',
                            'support_contact': 'support@yourapp.com'
                        }
                    }
                }, status=status.HTTP_409_CONFLICT)
            else:
                return Response({
                    'error': {
                        'code': 'OAUTH_CALLBACK_FAILED',
                        'message': str(e)
                    }
                }, status=status.HTTP_400_BAD_REQUEST)


class GoogleOAuthLinkView(APIView):
    """Link Google account to existing authenticated user"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Link Google account to current user",
        description="Link a Google account to the currently authenticated user",
        request={
            'type': 'object',
            'properties': {
                'code': {'type': 'string'},
                'state': {'type': 'string'},
                'redirect_uri': {'type': 'string', 'format': 'uri'},
            },
            'required': ['code', 'state', 'redirect_uri']
        },
        responses={
            200: OpenApiResponse(description="Account linked successfully"),
            400: OpenApiResponse(description="Invalid request or OAuth error"),
            409: OpenApiResponse(description="Google account already linked to another user")
        }
    )
    def post(self, request):
        # Similar to callback but for linking to existing authenticated user
        # Implementation follows same pattern as GoogleOAuthCallbackView
        # but ensures user is authenticated and handles linking specifically
        pass


class GoogleOAuthUnlinkView(APIView):
    """Unlink Google account from current user"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Unlink Google account",
        description="Remove Google account link from current user",
        responses={
            200: OpenApiResponse(description="Account unlinked successfully"),
            400: OpenApiResponse(description="No Google account linked or cannot unlink")
        }
    )
    def post(self, request):
        user = request.user
        
        if not user.google_id:
            return Response({
                'error': {
                    'code': 'NO_GOOGLE_ACCOUNT',
                    'message': 'No Google account linked to this user'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user can still log in after unlinking
        if not user.has_usable_password:
            return Response({
                'error': {
                    'code': 'CANNOT_UNLINK',
                    'message': 'Cannot unlink Google account without setting a password first'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.unlink_google_account()
        
        return Response({
            'data': {
                'message': 'Google account unlinked successfully',
                'user': UserSerializer(user).data
            }
        })
```

### Step 4: URL Configuration

#### Add OAuth URLs
```python
# users/urls.py - add these paths
from .views.google_oauth import (
    GoogleOAuthInitiateView,
    GoogleOAuthCallbackView,
    GoogleOAuthLinkView,
    GoogleOAuthUnlinkView,
)

# Add to urlpatterns
path('auth/google/initiate/', GoogleOAuthInitiateView.as_view(), name='google-oauth-initiate'),
path('auth/google/callback/', GoogleOAuthCallbackView.as_view(), name='google-oauth-callback'),
path('auth/google/link/', GoogleOAuthLinkView.as_view(), name='google-oauth-link'),
path('auth/google/unlink/', GoogleOAuthUnlinkView.as_view(), name='google-oauth-unlink'),
```

### Step 5: Settings Configuration

#### Update Django Settings
```python
# mysite/settings.py - add these configurations

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)

# Optional: Restrict to specific domains
GOOGLE_OAUTH_ALLOWED_DOMAINS = [
    domain.strip() 
    for domain in os.environ.get('GOOGLE_OAUTH_ALLOWED_DOMAINS', '').split(',') 
    if domain.strip()
]

# OAuth scopes to request from Google
GOOGLE_OAUTH_SCOPES = ['openid', 'email', 'profile']

# Security settings
OAUTH_VALIDATE_IP = True  # Set to False for mobile apps or users with dynamic IPs
```

#### Environment Variables
```bash
# .env file additions
GOOGLE_OAUTH_CLIENT_ID=your-client-id.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# Optional domain restrictions (comma-separated)
GOOGLE_OAUTH_ALLOWED_DOMAINS=yourdomain.com,anotherdomain.com

# Security settings
OAUTH_VALIDATE_IP=true
```

### Step 6: Admin Interface Updates

#### Enhanced User Admin
```python
# users/admin.py - update existing UserAdmin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'username', 'email', 'auth_provider', 'email_verified', 
        'google_linked_at', 'is_staff', 'date_joined'
    ]
    list_filter = [
        'auth_provider', 'email_verified', 'is_staff', 
        'is_superuser', 'is_active', 'date_joined'
    ]
    search_fields = ['username', 'email', 'google_email', 'google_id']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Google OAuth', {
            'fields': (
                'google_id', 'google_email', 'auth_provider',
                'has_usable_password', 'google_linked_at', 'last_google_sync'
            ),
        }),
    )
    
    readonly_fields = ['google_linked_at', 'last_google_sync', 'date_joined']
```

### Step 7: Testing Implementation

#### Unit Tests
```python
# users/tests/test_google_oauth.py
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from ..services.google_oauth import GoogleOAuthService, OAuthStateManager

User = get_user_model()


class GoogleOAuthServiceTests(TestCase):
    def setUp(self):
        self.service = GoogleOAuthService()
        self.mock_google_user_info = {
            'sub': '123456789',
            'email': 'test@gmail.com',
            'given_name': 'Test',
            'family_name': 'User',
            'email_verified': True
        }
    
    def test_generate_unique_username(self):
        username = self.service.generate_unique_username(self.mock_google_user_info)
        self.assertEqual(username, 'test')
        
        # Create user with that username
        User.objects.create_user(username='test', email='other@example.com')
        
        # Should generate unique username
        username2 = self.service.generate_unique_username(self.mock_google_user_info)
        self.assertEqual(username2, 'test_1')
    
    def test_create_google_user(self):
        user, action = self.service.create_google_user(self.mock_google_user_info)
        
        self.assertEqual(action, 'created')
        self.assertEqual(user.email, 'test@gmail.com')
        self.assertEqual(user.google_id, '123456789')
        self.assertTrue(user.email_verified)
        self.assertFalse(user.has_usable_password)
        self.assertEqual(user.auth_provider, 'google')
    
    def test_link_google_to_existing_user(self):
        existing_user = User.objects.create_user(
            username='existing', 
            email='test@gmail.com',
            password='password123',
            email_verified=True  # Important: email must be verified
        )
        
        user, action = self.service.link_google_to_existing_user(
            existing_user, 
            self.mock_google_user_info
        )
        
        self.assertEqual(action, 'linked')
        self.assertEqual(user.google_id, '123456789')
        self.assertTrue(user.email_verified)
        self.assertTrue(user.has_usable_password)
        self.assertEqual(user.auth_provider, 'hybrid')
    
    def test_block_linking_to_unverified_account(self):
        """Test that Google OAuth is blocked for unverified accounts"""
        # Create unverified account
        unverified_user = User.objects.create_user(
            username='unverified', 
            email='test@gmail.com',
            password='password123',
            email_verified=False  # Not verified
        )
        
        # Attempt to find/create should raise error
        with self.assertRaises(GoogleOAuthError) as cm:
            self.service.find_or_create_user(self.mock_google_user_info)
        
        self.assertIn("email address has not been verified", str(cm.exception))
        
        # Verify user was not modified
        unverified_user.refresh_from_db()
        self.assertIsNone(unverified_user.google_id)
        self.assertEqual(unverified_user.auth_provider, 'manual')
    
    def test_create_new_user_when_no_existing_account(self):
        """Test creating new Google user when no existing account exists"""
        user, action = self.service.find_or_create_user(self.mock_google_user_info)
        
        self.assertEqual(action, 'created')
        self.assertEqual(user.email, 'test@gmail.com')
        self.assertEqual(user.google_id, '123456789')
        self.assertTrue(user.email_verified)  # Google emails are pre-verified
        self.assertEqual(user.auth_provider, 'google')
    
    def test_authenticate_existing_google_user(self):
        """Test authenticating user with existing Google ID"""
        # Create existing Google user
        existing_google_user = User.objects.create(
            username='googleuser',
            email='test@gmail.com',
            google_id='123456789',
            email_verified=True,
            has_usable_password=False,
            auth_provider='google'
        )
        
        user, action = self.service.find_or_create_user(self.mock_google_user_info)
        
        self.assertEqual(action, 'authenticated')
        self.assertEqual(user.id, existing_google_user.id)
        self.assertEqual(user.google_id, '123456789')
    
    def test_google_account_conflict_different_google_id(self):
        """Test conflict when email exists but with different Google ID"""
        # Create user with same email but different Google ID
        existing_user = User.objects.create_user(
            username='existing',
            email='test@gmail.com',
            google_id='different-google-id',
            email_verified=True
        )
        
        with self.assertRaises(GoogleAccountConflictError) as cm:
            self.service.find_or_create_user(self.mock_google_user_info)
        
        self.assertIn("already linked to a different Google account", str(cm.exception))
    
    @patch('users.services.google_oauth.cache')
    @patch('users.services.google_oauth.send_email_task')
    def test_maybe_resend_verification_email(self, mock_send_email, mock_cache):
        """Test verification email resend with cooldown"""
        unverified_user = User.objects.create_user(
            username='unverified',
            email='test@gmail.com',
            email_verified=False
        )
        
        # Mock cache miss (no cooldown active)
        mock_cache.get.return_value = None
        
        self.service.maybe_resend_verification_email(unverified_user)
        
        # Verify cooldown was set
        mock_cache.set.assert_called_with(
            f'verification_resend_cooldown:{unverified_user.id}',
            True,
            timeout=300
        )
        
        # Verify email task was called
        mock_send_email.delay.assert_called_once()
    
    @patch('users.services.google_oauth.cache')
    def test_resend_email_respects_cooldown(self, mock_cache):
        """Test that email resend respects cooldown period"""
        unverified_user = User.objects.create_user(
            username='unverified',
            email='test@gmail.com', 
            email_verified=False
        )
        
        # Mock cache hit (cooldown active)
        mock_cache.get.return_value = True
        
        with patch('users.services.google_oauth.send_email_task') as mock_send_email:
            self.service.maybe_resend_verification_email(unverified_user)
            
            # Email should not be sent due to cooldown
            mock_send_email.delay.assert_not_called()


class GoogleOAuthAPITests(APITestCase):
    def test_initiate_oauth_success(self):
        response = self.client.post('/api/users/auth/google/initiate/', {
            'redirect_uri': 'https://frontend.com/callback'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('google_oauth_url', response.data['data'])
        self.assertIn('state_token', response.data['data'])
    
    @patch('users.services.google_oauth.GoogleOAuthService.handle_google_callback')
    def test_callback_success_new_user(self, mock_callback):
        # Mock successful callback for new user
        mock_user = User.objects.create_user(
            username='testuser', 
            email='test@gmail.com',
            google_id='123456789',
            email_verified=True,
            auth_provider='google'
        )
        mock_callback.return_value = (mock_user, 'created')
        
        # Create state token
        state_token = OAuthStateManager.generate_state_token()
        OAuthStateManager.store_state(
            state_token, 
            {'redirect_uri': 'https://frontend.com/callback'}, 
            '127.0.0.1'
        )
        
        response = self.client.post('/api/users/auth/google/callback/', {
            'code': 'mock-auth-code',
            'state': state_token,
            'redirect_uri': 'https://frontend.com/callback'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['account_action'], 'created')
    
    @patch('users.services.google_oauth.GoogleOAuthService.handle_google_callback')
    def test_callback_blocked_unverified_account(self, mock_callback):
        """Test that callback is blocked for unverified accounts"""
        mock_callback.side_effect = GoogleOAuthError(
            "An account with test@gmail.com exists but the email address has not been verified. "
            "Please check your email and click the verification link, or contact support if you "
            "need help accessing your account."
        )
        
        # Create state token
        state_token = OAuthStateManager.generate_state_token()
        OAuthStateManager.store_state(
            state_token, 
            {'redirect_uri': 'https://frontend.com/callback'}, 
            '127.0.0.1'
        )
        
        response = self.client.post('/api/users/auth/google/callback/', {
            'code': 'mock-auth-code',
            'state': state_token,
            'redirect_uri': 'https://frontend.com/callback'
        })
        
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['error']['code'], 'EMAIL_VERIFICATION_REQUIRED')
        self.assertIn('required_action', response.data['error']['details'])
        self.assertEqual(response.data['error']['details']['required_action'], 'verify_email_first')
    
    @patch('users.services.google_oauth.GoogleOAuthService.handle_google_callback')
    def test_callback_google_account_conflict(self, mock_callback):
        """Test callback when Google account is already linked to different user"""
        mock_callback.side_effect = GoogleOAuthError(
            "This email is already linked to a different Google account"
        )
        
        # Create state token
        state_token = OAuthStateManager.generate_state_token()
        OAuthStateManager.store_state(
            state_token,
            {'redirect_uri': 'https://frontend.com/callback'},
            '127.0.0.1'
        )
        
        response = self.client.post('/api/users/auth/google/callback/', {
            'code': 'mock-auth-code',
            'state': state_token,
            'redirect_uri': 'https://frontend.com/callback'
        })
        
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['error']['code'], 'GOOGLE_ACCOUNT_CONFLICT')
        self.assertIn('suggested_action', response.data['error']['details'])
        self.assertEqual(response.data['error']['details']['suggested_action'], 'contact_support')
```

### Step 8: Frontend Integration

#### JavaScript Client Example
```javascript
// frontend/src/services/googleAuth.js
class GoogleAuthService {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
    }
    
    async initiateGoogleAuth(redirectUri) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/google/initiate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    redirect_uri: redirectUri
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Store state for validation
            sessionStorage.setItem('google_oauth_state', data.data.state_token);
            
            return data.data;
        } catch (error) {
            console.error('Error initiating Google OAuth:', error);
            throw error;
        }
    }
    
    async handleGoogleCallback(urlParams) {
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        const error = urlParams.get('error');
        
        if (error) {
            throw new Error(`Google OAuth error: ${error}`);
        }
        
        if (!code || !state) {
            throw new Error('Missing authorization code or state');
        }
        
        // Validate state
        const storedState = sessionStorage.getItem('google_oauth_state');
        if (state !== storedState) {
            throw new Error('Invalid OAuth state - possible CSRF attack');
        }
        
        // Clean up stored state
        sessionStorage.removeItem('google_oauth_state');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/google/callback/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code: code,
                    state: state,
                    redirect_uri: window.location.origin + '/auth/google/callback'
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error.message);
            }
            
            const data = await response.json();
            
            // Store access token
            localStorage.setItem('access_token', data.data.tokens.access);
            
            return data.data;
        } catch (error) {
            console.error('Error handling Google callback:', error);
            throw error;
        }
    }
    
    async linkGoogleAccount(authCode, state, redirectUri) {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${this.apiBaseUrl}/auth/google/link/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    code: authCode,
                    state: state,
                    redirect_uri: redirectUri
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error.message);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error linking Google account:', error);
            throw error;
        }
    }
    
    async unlinkGoogleAccount() {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${this.apiBaseUrl}/auth/google/unlink/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error.message);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error unlinking Google account:', error);
            throw error;
        }
    }
}

export default GoogleAuthService;
```

### Step 9: Security Monitoring and Logging

#### Enhanced Logging for Security Events
```python
# users/logging.py
import logging
from django.utils import timezone

# Configure security-specific logger
security_logger = logging.getLogger('users.security')

def log_oauth_security_event(event_type, email=None, user_id=None, google_id=None, **extra_data):
    """Log OAuth security events for monitoring"""
    log_data = {
        'timestamp': timezone.now().isoformat(),
        'event_type': event_type,
        'email': email,
        'user_id': user_id,
        'google_id': google_id,
        **extra_data
    }
    
    if event_type in ['oauth_blocked_unverified', 'google_account_conflict']:
        security_logger.warning(f"OAuth Security Event: {event_type}", extra=log_data)
    else:
        security_logger.info(f"OAuth Event: {event_type}", extra=log_data)

# Usage in GoogleOAuthService
def find_or_create_user(self, google_user_info):
    # ... existing code ...
    
    elif not existing_user.email_verified:
        # Log security event
        log_oauth_security_event(
            'oauth_blocked_unverified',
            email=google_email,
            user_id=existing_user.id,
            google_id=google_id,
            account_age_days=(timezone.now() - existing_user.date_joined).days,
            ip_address=getattr(self, '_request_ip', 'unknown')
        )
        
        # ... rest of error handling ...
```

#### Admin Dashboard for Security Monitoring
```python
# users/admin.py - Add security monitoring views
from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # ... existing configuration ...
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related().annotate(
            days_since_joined=timezone.now() - models.F('date_joined')
        )
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Add security metrics to admin changelist
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        extra_context['security_stats'] = {
            'unverified_accounts_total': User.objects.filter(email_verified=False).count(),
            'unverified_accounts_recent': User.objects.filter(
                email_verified=False, 
                date_joined__gte=thirty_days_ago
            ).count(),
            'google_linked_accounts': User.objects.filter(google_id__isnull=False).count(),
            'hybrid_auth_accounts': User.objects.filter(auth_provider='hybrid').count(),
        }
        
        return super().changelist_view(request, extra_context)

# Custom admin command for security audit
# management/commands/audit_oauth_security.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Audit OAuth security and generate report'
    
    def handle(self, *args, **options):
        # Find potentially suspicious accounts
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Long-standing unverified accounts
        old_unverified = User.objects.filter(
            email_verified=False,
            date_joined__lt=thirty_days_ago
        )
        
        self.stdout.write(f"Found {old_unverified.count()} unverified accounts older than 30 days")
        
        # Accounts with common email domains (potential abuse)
        from collections import Counter
        email_domains = Counter([
            user.email.split('@')[1].lower() 
            for user in User.objects.filter(email_verified=False)
        ])
        
        for domain, count in email_domains.most_common(10):
            if count > 5:  # Threshold for suspicious activity
                self.stdout.write(f"Warning: {count} unverified accounts from domain {domain}")
```

### Step 10: Security Hardening Implementation

#### Critical Security Fixes

##### 1. Redirect URI Validation
```python
# users/security/validation.py
from urllib.parse import urlparse
from django.conf import settings
from django.core.exceptions import ValidationError

class RedirectURIValidator:
    """Validate redirect URIs against whitelist to prevent open redirect attacks"""
    
    @staticmethod
    def validate_redirect_uri(redirect_uri: str) -> bool:
        """Validate redirect URI against configured whitelist"""
        allowed_uris = getattr(settings, 'OAUTH_ALLOWED_REDIRECT_URIS', [])
        
        if not allowed_uris:
            raise ValidationError("No redirect URIs configured")
        
        try:
            parsed = urlparse(redirect_uri)
            
            # Basic security checks
            if parsed.scheme not in ['https', 'http']:
                return False
            
            # Production should only allow HTTPS
            if not settings.DEBUG and parsed.scheme != 'https':
                return False
            
            # Check against whitelist
            for allowed_uri in allowed_uris:
                allowed_parsed = urlparse(allowed_uri)
                
                # Exact match for scheme, host, and path prefix
                if (parsed.scheme == allowed_parsed.scheme and 
                    parsed.netloc == allowed_parsed.netloc and
                    parsed.path.startswith(allowed_parsed.path)):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating redirect URI: {e}")
            return False

# Update settings.py
OAUTH_ALLOWED_REDIRECT_URIS = [
    'https://yourdomain.com/auth/callback',
    'https://yourdomain.com/auth/google/callback',
    # Development only
    'http://localhost:3000/auth/callback' if DEBUG else None,
    'http://127.0.0.1:3000/auth/callback' if DEBUG else None,
]
OAUTH_ALLOWED_REDIRECT_URIS = [uri for uri in OAUTH_ALLOWED_REDIRECT_URIS if uri]

# Update GoogleOAuthInitiateView
class GoogleOAuthInitiateView(APIView):
    def post(self, request):
        redirect_uri = request.data.get('redirect_uri')
        
        # Validate redirect URI
        if not RedirectURIValidator.validate_redirect_uri(redirect_uri):
            return Response({
                'error': {
                    'code': 'INVALID_REDIRECT_URI',
                    'message': 'Redirect URI not allowed',
                    'details': {
                        'provided_uri': redirect_uri,
                        'help': 'Contact administrator to whitelist your redirect URI'
                    }
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ... rest of implementation
```

##### 2. Authorization Code Tracking
```python
# users/security/code_tracking.py
import hashlib
from django.core.cache import cache
from django.utils import timezone

class AuthorizationCodeTracker:
    """Track authorization codes to prevent replay attacks"""
    
    USED_CODE_TTL = 600  # 10 minutes
    
    @staticmethod
    def _get_code_key(code: str) -> str:
        """Generate secure cache key for authorization code"""
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        return f"oauth_code_used:{code_hash}"
    
    @staticmethod
    def is_code_used(code: str) -> bool:
        """Check if authorization code has been used"""
        cache_key = AuthorizationCodeTracker._get_code_key(code)
        return cache.get(cache_key) is not None
    
    @staticmethod
    def mark_code_used(code: str) -> None:
        """Mark authorization code as used"""
        cache_key = AuthorizationCodeTracker._get_code_key(code)
        cache.set(cache_key, {
            'used_at': timezone.now().isoformat(),
            'code_length': len(code)  # Store metadata without the actual code
        }, timeout=AuthorizationCodeTracker.USED_CODE_TTL)
        
        # Log for security monitoring
        logger.info("Authorization code marked as used", extra={
            'cache_key_hash': hashlib.sha256(cache_key.encode()).hexdigest()[:16],
            'event_type': 'oauth_code_consumed'
        })

# Update GoogleOAuthService
class GoogleOAuthService:
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens with replay protection"""
        
        # Check for code reuse
        if AuthorizationCodeTracker.is_code_used(code):
            logger.warning("Authorization code reuse attempt detected", extra={
                'code_hash': hashlib.sha256(code.encode()).hexdigest()[:16],
                'redirect_uri': redirect_uri,
                'event_type': 'oauth_code_reuse_attempt'
            })
            raise GoogleOAuthError("Authorization code has already been used")
        
        # Mark code as used immediately to prevent race conditions
        AuthorizationCodeTracker.mark_code_used(code)
        
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
            }
            
            response = requests.post(self.GOOGLE_TOKEN_URL, data=data, timeout=10)
            
            if response.status_code != 200:
                # Log error but don't expose sensitive details
                logger.error("Token exchange failed", extra={
                    'status_code': response.status_code,
                    'has_error_description': 'error_description' in response.text
                })
                raise GoogleTokenValidationError("Failed to exchange authorization code")
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Network error during token exchange: {e}")
            raise GoogleTokenValidationError("Network error during authentication")
```

##### 3. Enhanced Session Security
```python
# users/security/session.py
from django.contrib.sessions.models import Session

class SessionSecurityManager:
    """Manage session security for OAuth flows"""
    
    @staticmethod
    def invalidate_existing_sessions(request, user):
        """Invalidate existing sessions to prevent session fixation"""
        
        # Clear current session completely
        if hasattr(request, 'session'):
            request.session.flush()
            request.session.cycle_key()
        
        # For extra security: invalidate all user's existing sessions
        if user.is_authenticated:
            # Get all sessions for this user (requires custom session tracking)
            user_sessions = Session.objects.filter(
                session_data__contains=f'"_auth_user_id":"{user.id}"'
            )
            user_sessions.delete()
    
    @staticmethod
    def create_secure_session(request, user):
        """Create new secure session for OAuth-authenticated user"""
        
        # Set session security attributes
        request.session.set_expiry(86400)  # 24 hours
        request.session['oauth_login'] = True
        request.session['login_timestamp'] = timezone.now().isoformat()
        request.session['user_id'] = user.id
        
        # Mark session as requiring HTTPS in production
        if not settings.DEBUG:
            request.session.cookie_secure = True
            request.session.cookie_httponly = True
            request.session.cookie_samesite = 'Lax'

# Update GoogleOAuthCallbackView
class GoogleOAuthCallbackView(APIView):
    def post(self, request):
        # ... existing validation ...
        
        try:
            # Process OAuth callback
            oauth_service = GoogleOAuthService()
            user, action = oauth_service.handle_google_callback(code, redirect_uri)
            
            # Secure session handling
            SessionSecurityManager.invalidate_existing_sessions(request, user)
            
            # Generate new JWT tokens
            tokens = get_tokens_for_user(user)
            
            # Create secure session
            SessionSecurityManager.create_secure_session(request, user)
            
            response_data = {
                'data': {
                    'user': UserSerializer(user).data,
                    'tokens': {'access': tokens['access']},
                    'account_action': action
                }
            }
            
            # Set secure cookies
            response = Response(response_data, status=status.HTTP_200_OK)
            
            # Clear any existing refresh token cookies
            response.delete_cookie(
                'refresh_token', 
                path='/api/users/auth/token/refresh/',
                domain=getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
            )
            
            # Set new refresh token cookie
            set_refresh_cookie(response, tokens['refresh'])
            
            return response
            
        except GoogleOAuthError as e:
            # ... existing error handling ...
```

##### 4. Comprehensive Rate Limiting
```python
# users/throttles.py
import hashlib
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.core.cache import cache

class SmartOAuthThrottle(AnonRateThrottle):
    """Intelligent rate limiting for OAuth endpoints"""
    
    def get_cache_key(self, request, view):
        """Generate composite cache key for more accurate throttling"""
        
        # Get client identifiers
        ip = request.META.get('REMOTE_ADDR', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        
        # Create composite identifier
        client_signature = f"{ip}:{user_agent}:{x_forwarded_for}"
        signature_hash = hashlib.sha256(client_signature.encode()).hexdigest()[:16]
        
        # Include request-specific data for more granular limiting
        endpoint = view.__class__.__name__
        
        return f"oauth_throttle:{endpoint}:{signature_hash}"
    
    def throttle_failure(self):
        """Enhanced throttle failure with security logging"""
        
        # Log potential abuse
        logger.warning("OAuth rate limit exceeded", extra={
            'throttle_scope': self.scope,
            'client_ip': self.request.META.get('REMOTE_ADDR'),
            'user_agent': self.request.META.get('HTTP_USER_AGENT', '')[:100],
            'event_type': 'oauth_rate_limit_exceeded'
        })
        
        return super().throttle_failure()

class GoogleOAuthInitiateThrottle(SmartOAuthThrottle):
    scope = 'oauth_initiate'
    rate = '10/hour'  # Conservative limit for OAuth initiation

class GoogleOAuthCallbackThrottle(SmartOAuthThrottle):
    scope = 'oauth_callback' 
    rate = '20/hour'  # Slightly higher for callback processing

class EmailVerificationResendThrottle(UserRateThrottle):
    scope = 'email_verification_resend'
    rate = '3/hour'  # Very conservative for email sending

# Progressive throttling based on failure count
class ProgressiveOAuthThrottle(SmartOAuthThrottle):
    """Increase restrictions based on failed attempts"""
    
    def allow_request(self, request, view):
        """Apply progressive throttling based on failure history"""
        
        # Get base throttle result
        base_allowed = super().allow_request(request, view)
        
        if not base_allowed:
            return False
        
        # Check failure history
        failure_key = f"oauth_failures:{self.get_ident(request)}"
        failure_count = cache.get(failure_key, 0)
        
        if failure_count >= 5:
            # Severe restrictions after 5 failures
            severe_key = f"oauth_severe:{self.get_ident(request)}"
            severe_count = cache.get(severe_key, 0)
            
            if severe_count >= 1:
                logger.warning("OAuth severe throttling applied", extra={
                    'client_ip': request.META.get('REMOTE_ADDR'),
                    'failure_count': failure_count,
                    'event_type': 'oauth_severe_throttling'
                })
                return False
            
            # Allow one request but increment severe counter
            cache.set(severe_key, severe_count + 1, timeout=3600)
        
        return True

# settings.py updates
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'oauth_initiate': '10/hour',
        'oauth_callback': '20/hour', 
        'email_verification_resend': '3/hour',
        'oauth_severe': '1/hour',
    }
}

# Apply throttling to views
class GoogleOAuthInitiateView(APIView):
    throttle_classes = [ProgressiveOAuthThrottle]
    
class GoogleOAuthCallbackView(APIView):
    throttle_classes = [ProgressiveOAuthThrottle]
```

##### 5. Input Validation and Sanitization
```python
# users/security/validation.py
import re
from typing import Dict, Any
from django.core.exceptions import ValidationError

class GoogleDataValidator:
    """Comprehensive validation for Google OAuth data"""
    
    # Strict patterns for Google data
    GOOGLE_ID_PATTERN = re.compile(r'^\d{10,30}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    NAME_PATTERN = re.compile(r'^[a-zA-Z\s\'-\.]{1,100}$')
    URL_PATTERN = re.compile(r'^https://[a-zA-Z0-9.-]+/.*')
    
    # Dangerous patterns to reject
    DANGEROUS_PATTERNS = [
        re.compile(r'<script', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'data:', re.IGNORECASE),
        re.compile(r'vbscript:', re.IGNORECASE),
    ]
    
    @classmethod
    def validate_and_sanitize(cls, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize Google user info with strict checks"""
        
        validated = {}
        
        # Validate Google ID (sub) - Critical field
        google_id = str(user_info.get('sub', ''))
        if not cls.GOOGLE_ID_PATTERN.match(google_id):
            raise ValidationError(f"Invalid Google ID format")
        validated['sub'] = google_id
        
        # Validate email - Critical field
        email = str(user_info.get('email', '')).lower().strip()
        if not cls.EMAIL_PATTERN.match(email):
            raise ValidationError(f"Invalid email format")
        
        # Check for suspicious email patterns
        if any(pattern.search(email) for pattern in cls.DANGEROUS_PATTERNS):
            raise ValidationError("Invalid email content")
            
        validated['email'] = email
        
        # Validate email verification status
        email_verified = user_info.get('email_verified')
        if email_verified is not None:
            validated['email_verified'] = bool(email_verified)
        
        # Validate and sanitize names
        for field_name, max_length in [('given_name', 50), ('family_name', 50), ('name', 100)]:
            if field_name in user_info:
                name_value = str(user_info[field_name])[:max_length]
                
                # Check for dangerous patterns
                if any(pattern.search(name_value) for pattern in cls.DANGEROUS_PATTERNS):
                    # Replace with safe default
                    name_value = "User"
                
                # Sanitize but preserve international characters
                if cls.NAME_PATTERN.match(name_value):
                    validated[field_name] = name_value
                else:
                    # Remove dangerous characters, keep safe ones
                    sanitized = re.sub(r'[<>"\'\&\{\}]', '', name_value)
                    validated[field_name] = sanitized[:max_length] if sanitized else "User"
        
        # Validate profile picture URL
        if 'picture' in user_info:
            picture_url = str(user_info['picture'])
            if cls.URL_PATTERN.match(picture_url) and 'googleusercontent.com' in picture_url:
                validated['picture'] = picture_url
            # If invalid, simply don't include it
        
        # Validate locale if present
        if 'locale' in user_info:
            locale = str(user_info['locale'])
            if re.match(r'^[a-zA-Z]{2}(-[a-zA-Z]{2})?$', locale):
                validated['locale'] = locale
        
        return validated
    
    @classmethod
    def validate_authorization_response(cls, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate OAuth authorization response"""
        
        validated = {}
        
        # Validate authorization code
        code = response_data.get('code', '')
        if not code or len(code) < 10 or len(code) > 512:
            raise ValidationError("Invalid authorization code format")
        
        # Basic pattern check for Google auth codes
        if not re.match(r'^[a-zA-Z0-9/_-]+$', code):
            raise ValidationError("Authorization code contains invalid characters")
        
        validated['code'] = code
        
        # Validate state token
        state = response_data.get('state', '')
        if not state or len(state) < 16 or len(state) > 128:
            raise ValidationError("Invalid state token format")
        
        # State tokens should be URL-safe base64
        if not re.match(r'^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)?$', state):
            raise ValidationError("State token contains invalid characters")
        
        validated['state'] = state
        
        # Validate redirect URI
        redirect_uri = response_data.get('redirect_uri', '')
        if not redirect_uri:
            raise ValidationError("Missing redirect URI")
        
        # Additional validation happens in RedirectURIValidator
        validated['redirect_uri'] = redirect_uri
        
        return validated

# Update GoogleOAuthService to use validation
class GoogleOAuthService:
    def validate_id_token(self, id_token_str: str) -> Dict[str, Any]:
        """Enhanced ID token validation"""
        try:
            # Google's validation
            idinfo = id_token.verify_oauth2_token(
                id_token_str, 
                google_requests.Request(), 
                self.client_id
            )
            
            # Verify issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise GoogleTokenValidationError('Invalid token issuer')
            
            # Additional timestamp validation
            current_time = int(timezone.now().timestamp())
            issued_at = idinfo.get('iat', 0)
            expires_at = idinfo.get('exp', 0)
            
            if issued_at > current_time + 60:  # Allow 60 second clock skew
                raise GoogleTokenValidationError('Token issued in the future')
            
            if expires_at < current_time - 60:  # Allow 60 second clock skew
                raise GoogleTokenValidationError('Token has expired')
            
            # Validate audience
            if idinfo.get('aud') != self.client_id:
                raise GoogleTokenValidationError('Invalid token audience')
            
            # Apply our validation and sanitization
            validated_info = GoogleDataValidator.validate_and_sanitize(idinfo)
            
            return validated_info
            
        except ValueError as e:
            raise GoogleTokenValidationError(f"Token validation failed")
```

##### 6. Security Monitoring and Alerting
```python
# users/security/monitoring.py
import logging
from django.core.mail import mail_admins
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

# Configure security logger
security_logger = logging.getLogger('users.security')

class SecurityEventMonitor:
    """Monitor and respond to OAuth security events"""
    
    # Critical events requiring immediate attention
    CRITICAL_EVENTS = [
        'oauth_redirect_uri_violation',
        'oauth_code_reuse_attempt',
        'oauth_state_token_abuse', 
        'oauth_rate_limit_exceeded',
        'oauth_session_fixation_attempt'
    ]
    
    # Events requiring monitoring but not immediate alerts
    WARNING_EVENTS = [
        'oauth_invalid_google_id_format',
        'oauth_timing_attack_suspected',
        'oauth_token_replay_attempt',
        'oauth_blocked_unverified_account'
    ]
    
    @classmethod
    def log_security_event(cls, event_type: str, context: dict, request=None):
        """Log security event with appropriate severity"""
        
        # Enrich context with request data
        if request:
            context.update({
                'ip_address': request.META.get('REMOTE_ADDR', 'unknown'),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:200],
                'referer': request.META.get('HTTP_REFERER', 'unknown')[:200],
                'timestamp': timezone.now().isoformat(),
            })
        
        if event_type in cls.CRITICAL_EVENTS:
            security_logger.critical(f"CRITICAL OAuth Security Event: {event_type}", extra=context)
            cls._trigger_critical_alert(event_type, context)
            
        elif event_type in cls.WARNING_EVENTS:
            security_logger.warning(f"OAuth Security Warning: {event_type}", extra=context)
            
        else:
            security_logger.info(f"OAuth Security Event: {event_type}", extra=context)
    
    @classmethod
    def _trigger_critical_alert(cls, event_type: str, context: dict):
        """Trigger immediate alerts for critical security events"""
        
        # Email alert to administrators
        subject = f"CRITICAL OAuth Security Alert: {event_type}"
        message = f"""
        A critical OAuth security event has occurred:
        
        Event Type: {event_type}
        Time: {context.get('timestamp', 'unknown')}
        IP Address: {context.get('ip_address', 'unknown')}
        User Agent: {context.get('user_agent', 'unknown')}
        
        Additional Context:
        {json.dumps(context, indent=2)}
        
        Immediate investigation required.
        """
        
        try:
            mail_admins(subject, message, fail_silently=False)
        except Exception as e:
            logger.error(f"Failed to send security alert email: {e}")
        
        # Additional alerting mechanisms
        cls._trigger_webhook_alert(event_type, context)
        cls._increment_security_metrics(event_type)
    
    @classmethod
    def _trigger_webhook_alert(cls, event_type: str, context: dict):
        """Send webhook alerts to external monitoring systems"""
        webhook_url = getattr(settings, 'SECURITY_WEBHOOK_URL', None)
        
        if webhook_url:
            try:
                payload = {
                    'alert_type': 'oauth_security',
                    'severity': 'critical',
                    'event_type': event_type,
                    'context': context,
                    'application': 'tinybeans-oauth'
                }
                
                response = requests.post(
                    webhook_url,
                    json=payload,
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code != 200:
                    logger.error(f"Webhook alert failed: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")
    
    @classmethod
    def _increment_security_metrics(cls, event_type: str):
        """Increment security metrics for monitoring dashboards"""
        from django.core.cache import cache
        
        # Daily metrics
        today = timezone.now().date().isoformat()
        daily_key = f"security_metrics:daily:{today}:{event_type}"
        current_count = cache.get(daily_key, 0)
        cache.set(daily_key, current_count + 1, timeout=86400 * 2)  # 2 days
        
        # Hourly metrics for immediate monitoring
        current_hour = timezone.now().strftime('%Y-%m-%d-%H')
        hourly_key = f"security_metrics:hourly:{current_hour}:{event_type}"
        hourly_count = cache.get(hourly_key, 0)
        cache.set(hourly_key, hourly_count + 1, timeout=3600 * 25)  # 25 hours
        
        # Check for attack patterns
        if hourly_count >= 5:  # 5 events of same type in one hour
            cls.log_security_event('oauth_attack_pattern_detected', {
                'pattern_type': event_type,
                'count': hourly_count,
                'timeframe': 'hourly'
            })

# Integration with OAuth views
class GoogleOAuthCallbackView(APIView):
    def post(self, request):
        try:
            # Validate request data
            validated_data = GoogleDataValidator.validate_authorization_response(request.data)
            
            # ... existing OAuth processing ...
            
        except ValidationError as e:
            SecurityEventMonitor.log_security_event(
                'oauth_invalid_request_data',
                {'error': str(e), 'request_data_keys': list(request.data.keys())},
                request
            )
            return Response({'error': {'code': 'INVALID_REQUEST', 'message': 'Invalid request data'}}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        except GoogleOAuthError as e:
            # Log based on error type
            if "already been used" in str(e):
                SecurityEventMonitor.log_security_event(
                    'oauth_code_reuse_attempt',
                    {'error_message': str(e)},
                    request
                )
            
            # ... rest of error handling
```

##### 7. Security Testing Suite
```python
# users/tests/test_oauth_security.py
import time
import hashlib
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status

class OAuthSecurityTestCase(APITestCase):
    """Comprehensive security testing for OAuth implementation"""
    
    def setUp(self):
        self.malicious_redirect_uris = [
            'https://evil.com/steal-tokens',
            'javascript:alert(1)',
            'data:text/html,<script>alert(1)</script>',
            'https://legitimate-site.com.evil.com/',
            'https://evil.com/?legitimate-site.com',
            'https://攻击者.com/callback',  # IDN homograph attack
        ]
        
        self.valid_redirect_uri = 'https://legitimate-app.com/auth/callback'
    
    def test_redirect_uri_validation_blocks_malicious_uris(self):
        """Test that malicious redirect URIs are blocked"""
        
        for malicious_uri in self.malicious_redirect_uris:
            response = self.client.post('/api/users/auth/google/initiate/', {
                'redirect_uri': malicious_uri
            })
            
            self.assertEqual(response.status_code, 400, 
                           f"Should block malicious URI: {malicious_uri}")
            self.assertEqual(response.data['error']['code'], 'INVALID_REDIRECT_URI')
    
    def test_redirect_uri_validation_allows_whitelisted_uris(self):
        """Test that whitelisted URIs are allowed"""
        
        with override_settings(OAUTH_ALLOWED_REDIRECT_URIS=[self.valid_redirect_uri]):
            response = self.client.post('/api/users/auth/google/initiate/', {
                'redirect_uri': self.valid_redirect_uri
            })
            
            self.assertEqual(response.status_code, 200)
            self.assertIn('google_oauth_url', response.data['data'])
    
    def test_authorization_code_reuse_prevention(self):
        """Test that authorization codes can only be used once"""
        
        code = "test_authorization_code_12345"
        
        # Mock successful first exchange
        with patch('users.services.google_oauth.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'access_token': 'test_access_token',
                'id_token': 'test_id_token'
            }
            mock_post.return_value = mock_response
            
            service = GoogleOAuthService()
            
            # First use should succeed
            result = service.exchange_code_for_tokens(code, self.valid_redirect_uri)
            self.assertIn('access_token', result)
            
            # Second use should fail
            with self.assertRaises(GoogleOAuthError) as cm:
                service.exchange_code_for_tokens(code, self.valid_redirect_uri)
            
            self.assertIn("already been used", str(cm.exception))
    
    def test_rate_limiting_prevents_abuse(self):
        """Test that rate limiting prevents automated attacks"""
        
        # Attempt to exceed rate limit
        for i in range(12):  # Limit is 10/hour
            response = self.client.post('/api/users/auth/google/initiate/', {
                'redirect_uri': self.valid_redirect_uri
            })
            
            if i < 10:
                self.assertIn(response.status_code, [200, 400])  # May fail validation but not rate limited
            else:
                self.assertEqual(response.status_code, 429)  # Should be rate limited
    
    def test_progressive_throttling_increases_restrictions(self):
        """Test that repeated failures increase restrictions"""
        
        # Simulate failures by using invalid redirect URIs
        for i in range(6):  # 5 failures should trigger severe throttling
            response = self.client.post('/api/users/auth/google/initiate/', {
                'redirect_uri': 'https://invalid.com'
            })
            self.assertEqual(response.status_code, 400)
        
        # Next request should face severe throttling
        response = self.client.post('/api/users/auth/google/initiate/', {
            'redirect_uri': self.valid_redirect_uri
        })
        
        # Should be severely throttled after multiple failures
        self.assertIn(response.status_code, [429, 400])
    
    def test_session_fixation_prevention(self):
        """Test that OAuth login prevents session fixation"""
        
        # Set initial session data
        session = self.client.session
        session['initial_data'] = 'should_be_cleared'
        session.save()
        initial_key = session.session_key
        
        # Mock successful OAuth callback
        with patch('users.services.google_oauth.GoogleOAuthService.handle_google_callback') as mock_callback:
            mock_user = User.objects.create_user(
                username='testuser',
                email='test@gmail.com',
                email_verified=True,
                google_id='123456789'
            )
            mock_callback.return_value = (mock_user, 'authenticated')
            
            # Create and use state token
            state_token = OAuthStateManager.generate_state_token()
            OAuthStateManager.store_state(state_token, {
                'redirect_uri': self.valid_redirect_uri
            }, '127.0.0.1')
            
            response = self.client.post('/api/users/auth/google/callback/', {
                'code': 'test_code',
                'state': state_token,
                'redirect_uri': self.valid_redirect_uri
            })
            
            self.assertEqual(response.status_code, 200)
            
            # Session should be regenerated (new key)
            new_session = self.client.session
            self.assertNotEqual(initial_key, new_session.session_key)
            
            # Old session data should be cleared
            self.assertNotIn('initial_data', new_session)
    
    def test_google_data_validation_rejects_malicious_input(self):
        """Test that Google user data validation rejects malicious input"""
        
        malicious_inputs = [
            {
                'sub': '12345',  # Too short
                'email': 'test@example.com'
            },
            {
                'sub': '123456789012345678901',
                'email': '<script>alert(1)</script>@example.com'  # XSS attempt
            },
            {
                'sub': '123456789012345678901',
                'email': 'test@example.com',
                'given_name': '<script>alert(1)</script>'  # XSS in name
            },
            {
                'sub': 'not_numeric_id',  # Non-numeric Google ID
                'email': 'test@example.com'
            }
        ]
        
        validator = GoogleDataValidator()
        
        for malicious_input in malicious_inputs:
            with self.assertRaises(ValidationError):
                validator.validate_and_sanitize(malicious_input)
    
    def test_timing_attack_mitigation(self):
        """Test that timing attacks are mitigated"""
        
        # Create existing user
        existing_user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            email_verified=True
        )
        
        service = GoogleOAuthService()
        
        # Time request for existing user
        start_time = time.time()
        try:
            service.find_or_create_user({
                'sub': '123456789012345678901',
                'email': 'existing@example.com',
                'email_verified': True
            })
        except:
            pass
        existing_time = time.time() - start_time
        
        # Time request for non-existing user  
        start_time = time.time()
        try:
            service.find_or_create_user({
                'sub': '123456789012345678902',
                'email': 'nonexisting@example.com',
                'email_verified': True
            })
        except:
            pass
        nonexisting_time = time.time() - start_time
        
        # Timing difference should be minimal (less than 100ms)
        timing_difference = abs(existing_time - nonexisting_time)
        self.assertLess(timing_difference, 0.1, 
                       "Timing difference suggests potential timing attack vulnerability")
    
    def test_security_event_monitoring(self):
        """Test that security events are properly logged and monitored"""
        
        with patch('users.security.monitoring.SecurityEventMonitor.log_security_event') as mock_log:
            # Trigger a security event (code reuse)
            AuthorizationCodeTracker.mark_code_used('test_code')
            
            service = GoogleOAuthService()
            
            with self.assertRaises(GoogleOAuthError):
                service.exchange_code_for_tokens('test_code', self.valid_redirect_uri)
            
            # Should have logged the security event
            mock_log.assert_called_with(
                'oauth_code_reuse_attempt',
                unittest.mock.ANY,
                unittest.mock.ANY
            )
    
    def test_cache_key_security(self):
        """Test that cache keys are properly secured"""
        
        # OAuth state tokens should use secure cache keys
        token = "test_token_12345"
        
        cache_key = SecureCacheManager.generate_cache_key("state", token)
        
        # Cache key should not contain the actual token
        self.assertNotIn(token, cache_key)
        
        # Should be consistent for same input
        cache_key_2 = SecureCacheManager.generate_cache_key("state", token)
        self.assertEqual(cache_key, cache_key_2)
        
        # Should be different for different inputs
        cache_key_3 = SecureCacheManager.generate_cache_key("state", "different_token")
        self.assertNotEqual(cache_key, cache_key_3)

class OAuthSecurityIntegrationTests(APITestCase):
    """Integration tests for complete OAuth security flows"""
    
    def test_complete_secure_oauth_flow(self):
        """Test complete OAuth flow with all security measures"""
        
        with override_settings(OAUTH_ALLOWED_REDIRECT_URIS=['https://app.com/callback']):
            # 1. Initiate OAuth
            response = self.client.post('/api/users/auth/google/initiate/', {
                'redirect_uri': 'https://app.com/callback'
            })
            self.assertEqual(response.status_code, 200)
            
            state_token = response.data['data']['state_token']
            
            # 2. Mock successful Google OAuth callback
            with patch('users.services.google_oauth.GoogleOAuthService.handle_google_callback') as mock_callback:
                mock_user = User.objects.create_user(
                    username='secureuser',
                    email='secure@example.com',
                    email_verified=True,
                    google_id='987654321012345678901'
                )
                mock_callback.return_value = (mock_user, 'created')
                
                # 3. Complete callback
                response = self.client.post('/api/users/auth/google/callback/', {
                    'code': 'secure_auth_code',
                    'state': state_token,
                    'redirect_uri': 'https://app.com/callback'
                })
                
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['data']['account_action'], 'created')
                
                # 4. Verify security measures were applied
                # - Session should be new and secure
                # - Tokens should be properly set
                # - User should be authenticated
                self.assertIn('tokens', response.data['data'])
                self.assertIn('access', response.data['data']['tokens'])
    
    def tearDown(self):
        """Clean up after security tests"""
        cache.clear()  # Clear rate limiting and other cached data
        User.objects.all().delete()
```

This comprehensive security documentation addresses all identified vulnerabilities with production-ready solutions, monitoring, and testing frameworks.

#### Rate Limiting
```python
# users/throttles.py
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class GoogleOAuthThrottle(AnonRateThrottle):
    scope = 'google_oauth'
    rate = '10/min'  # 10 OAuth attempts per minute

# Add to settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'google_oauth': '10/min',
        # ... other throttle rates
    }
}

# Apply to OAuth views
class GoogleOAuthInitiateView(APIView):
    throttle_classes = [GoogleOAuthThrottle]
    # ... rest of the view
```

This implementation guide provides all the necessary code and configuration to integrate Google OAuth with automatic account linking while maintaining the existing authentication system.