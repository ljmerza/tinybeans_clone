"""OAuth security validators and utilities.

This module provides security validation functions for OAuth flows including:
- Redirect URI validation
- State token validation  
- PKCE validation
- Security logging
"""
import logging
import secrets
from typing import List, Optional
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('oauth.security')


class RedirectURIValidator:
    """Validates redirect URIs against whitelist to prevent open redirect attacks."""
    
    @staticmethod
    def validate(redirect_uri: str, allowed_uris: Optional[List[str]] = None) -> bool:
        """Validate redirect URI against whitelist.
        
        Performs strict validation:
        - Exact match for scheme (http/https)
        - Exact match for netloc (domain:port)
        - Path must match or be subpath of allowed path
        
        Args:
            redirect_uri: The redirect URI to validate
            allowed_uris: Optional list of allowed URIs (defaults to settings)
            
        Returns:
            bool: True if redirect URI is valid, False otherwise
        """
        if allowed_uris is None:
            allowed_uris = settings.OAUTH_ALLOWED_REDIRECT_URIS
        
        try:
            parsed_uri = urlparse(redirect_uri)
            
            # Basic validation
            if not parsed_uri.scheme or not parsed_uri.netloc:
                logger.warning(
                    "Invalid redirect URI format",
                    extra={
                        'event': 'oauth.redirect_uri_validation_failed',
                        'redirect_uri': redirect_uri,
                        'reason': 'missing_scheme_or_netloc'
                    }
                )
                return False
            
            # Check against whitelist
            for allowed_uri in allowed_uris:
                allowed_parsed = urlparse(allowed_uri)
                
                # Exact match for scheme and netloc
                # Path can be exact match or subpath
                if (parsed_uri.scheme == allowed_parsed.scheme and
                    parsed_uri.netloc == allowed_parsed.netloc and
                    parsed_uri.path.startswith(allowed_parsed.path)):
                    
                    logger.debug(
                        "Redirect URI validated",
                        extra={
                            'event': 'oauth.redirect_uri_validated',
                            'redirect_uri': redirect_uri,
                            'matched_whitelist_entry': allowed_uri
                        }
                    )
                    return True
            
            # No match found
            logger.warning(
                "Redirect URI not in whitelist",
                extra={
                    'event': 'oauth.redirect_uri_not_whitelisted',
                    'redirect_uri': redirect_uri,
                    'whitelist_size': len(allowed_uris)
                }
            )
            return False
            
        except Exception as e:
            logger.error(
                f"Redirect URI validation error: {str(e)}",
                extra={
                    'event': 'oauth.redirect_uri_validation_error',
                    'redirect_uri': redirect_uri,
                    'error': str(e)
                },
                exc_info=True
            )
            return False


class PKCEValidator:
    """Validates PKCE (Proof Key for Code Exchange) implementation."""
    
    @staticmethod
    def validate_code_verifier(code_verifier: str) -> bool:
        """Validate code verifier meets RFC 7636 requirements.
        
        Requirements:
        - Length: 43-128 characters
        - Characters: [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
        
        Args:
            code_verifier: The code verifier to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check length
        if not (43 <= len(code_verifier) <= 128):
            logger.warning(
                "Invalid code verifier length",
                extra={
                    'event': 'oauth.pkce_validation_failed',
                    'reason': 'invalid_length',
                    'length': len(code_verifier)
                }
            )
            return False
        
        # Check characters (RFC 7636 unreserved characters)
        allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~')
        if not all(c in allowed_chars for c in code_verifier):
            logger.warning(
                "Invalid code verifier characters",
                extra={
                    'event': 'oauth.pkce_validation_failed',
                    'reason': 'invalid_characters'
                }
            )
            return False
        
        return True


class StateTokenValidator:
    """Validates OAuth state tokens for CSRF protection."""
    
    @staticmethod
    def is_secure_token(token: str) -> bool:
        """Check if token meets minimum security requirements.
        
        Requirements:
        - Length: 128+ characters
        - High entropy (not predictable)
        
        Args:
            token: The state token to validate
            
        Returns:
            bool: True if token is secure, False otherwise
        """
        # Minimum length check
        if len(token) < 128:
            logger.warning(
                "State token too short",
                extra={
                    'event': 'oauth.state_validation_failed',
                    'reason': 'token_too_short',
                    'length': len(token)
                }
            )
            return False
        
        # Check for sufficient character variety (basic entropy check)
        unique_chars = len(set(token))
        if unique_chars < 32:  # Should have good variety
            logger.warning(
                "State token low entropy",
                extra={
                    'event': 'oauth.state_validation_failed',
                    'reason': 'low_entropy',
                    'unique_chars': unique_chars
                }
            )
            return False
        
        return True
    
    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks.
        
        Args:
            a: First string
            b: Second string
            
        Returns:
            bool: True if strings match, False otherwise
        """
        return secrets.compare_digest(a, b)


class SecurityLogger:
    """Centralized security logging for OAuth events."""
    
    @staticmethod
    def log_oauth_initiate(redirect_uri: str, ip_address: str, user_agent: str, state_token: str):
        """Log OAuth flow initiation."""
        logger.info(
            "OAuth flow initiated",
            extra={
                'event': 'oauth.initiate',
                'redirect_uri': redirect_uri,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'state_preview': state_token[:8] + '...' if state_token else None,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @staticmethod
    def log_oauth_callback_success(user_id: int, action: str, ip_address: str, google_id: str):
        """Log successful OAuth callback."""
        logger.info(
            f"OAuth callback successful - {action}",
            extra={
                'event': 'oauth.callback.success',
                'user_id': user_id,
                'action': action,
                'ip_address': ip_address,
                'google_id': google_id,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @staticmethod
    def log_oauth_callback_failure(reason: str, ip_address: str, details: dict = None):
        """Log failed OAuth callback."""
        extra = {
            'event': 'oauth.callback.failure',
            'reason': reason,
            'ip_address': ip_address,
            'timestamp': timezone.now().isoformat(),
        }
        if details:
            extra.update(details)
        
        logger.warning(f"OAuth callback failed: {reason}", extra=extra)
    
    @staticmethod
    def log_security_block(reason: str, email: str, ip_address: str, details: dict = None):
        """Log security block (e.g., unverified account)."""
        extra = {
            'event': 'oauth.security_block',
            'reason': reason,
            'email': email,
            'ip_address': ip_address,
            'timestamp': timezone.now().isoformat(),
        }
        if details:
            extra.update(details)
        
        logger.warning(f"OAuth blocked: {reason}", extra=extra)
    
    @staticmethod
    def log_account_action(action: str, user_id: int, google_id: str, ip_address: str):
        """Log account creation or linking."""
        logger.info(
            f"OAuth account action: {action}",
            extra={
                'event': f'oauth.account_{action}',
                'user_id': user_id,
                'google_id': google_id,
                'ip_address': ip_address,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @staticmethod
    def log_rate_limit_exceeded(endpoint: str, ip_address: str):
        """Log rate limit trigger."""
        logger.warning(
            f"OAuth rate limit exceeded: {endpoint}",
            extra={
                'event': 'oauth.rate_limit_exceeded',
                'endpoint': endpoint,
                'ip_address': ip_address,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @staticmethod
    def log_suspicious_activity(activity_type: str, ip_address: str, details: dict):
        """Log suspicious OAuth activity."""
        extra = {
            'event': 'oauth.suspicious_activity',
            'activity_type': activity_type,
            'ip_address': ip_address,
            'timestamp': timezone.now().isoformat(),
        }
        extra.update(details)
        
        logger.warning(f"Suspicious OAuth activity: {activity_type}", extra=extra)


def get_client_ip(request) -> str:
    """Extract client IP address from request.
    
    Handles X-Forwarded-For header for proxied requests.
    
    Args:
        request: Django request object
        
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the chain
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip


def get_user_agent(request) -> str:
    """Extract user agent from request.
    
    Args:
        request: Django request object
        
    Returns:
        str: User agent string
    """
    return request.META.get('HTTP_USER_AGENT', 'Unknown')
