# Google OAuth Security Vulnerability Analysis & Mitigation

## Overview
This document provides a comprehensive security analysis of the Google OAuth integration implementation, identifying potential vulnerabilities and providing detailed mitigation strategies.

## Executive Summary

### Vulnerability Summary
- **High Risk**: 2 vulnerabilities (Open Redirect, Session Fixation)
- **Medium Risk**: 5 vulnerabilities (Code Reuse, CSRF Bypass, DoS, etc.)
- **Low Risk**: 4 vulnerabilities (Information Disclosure, Timing Attacks, etc.)

### Critical Findings
1. **Open Redirect Vulnerability**: Unvalidated redirect URIs could enable phishing attacks
2. **Session Fixation Risk**: Sessions not properly invalidated during OAuth login
3. **Authorization Code Reuse**: No tracking to prevent code replay attacks
4. **Rate Limiting Gaps**: OAuth endpoints vulnerable to automated attacks

## Detailed Vulnerability Analysis

### 1. High Risk Vulnerabilities

#### 1.1 Open Redirect Vulnerability
**Severity**: High | **CVSS Score**: 7.4  
**CWE**: CWE-601 - URL Redirection to Untrusted Site

**Description**: The system accepts arbitrary redirect URIs without validation, allowing attackers to redirect users to malicious sites after OAuth completion.

**Vulnerable Code**:
```python
# users/views/google_oauth.py
def post(self, request):
    redirect_uri = request.data.get('redirect_uri')
    # No validation of redirect_uri against whitelist
    state_data = {'redirect_uri': redirect_uri, ...}
```

**Attack Scenario**:
1. Attacker initiates OAuth with malicious redirect URI: `https://evil.com/steal-tokens`
2. User completes Google OAuth successfully
3. System redirects user to attacker's domain with auth tokens
4. Attacker steals authentication tokens

**Impact**: Complete account takeover, credential theft, phishing attacks

**Mitigation Strategy**:
```python
# Settings configuration
OAUTH_ALLOWED_REDIRECT_URIS = [
    'https://yourdomain.com/auth/callback',
    'https://yourdomain.com/auth/google/callback',
    'http://localhost:3000/auth/callback',  # Development only
]

# Validation function
def validate_redirect_uri(self, redirect_uri: str) -> bool:
    """Validate redirect URI against whitelist"""
    allowed_uris = getattr(settings, 'OAUTH_ALLOWED_REDIRECT_URIS', [])
    
    # Parse and validate URI
    try:
        parsed = urlparse(redirect_uri)
        
        # Check if URI is in whitelist
        for allowed_uri in allowed_uris:
            allowed_parsed = urlparse(allowed_uri)
            
            # Exact match for scheme, host, and path prefix
            if (parsed.scheme == allowed_parsed.scheme and 
                parsed.netloc == allowed_parsed.netloc and
                parsed.path.startswith(allowed_parsed.path)):
                return True
        
        return False
    except Exception:
        return False
```

#### 1.2 Session Fixation Vulnerability  
**Severity**: High | **CVSS Score**: 6.8  
**CWE**: CWE-384 - Session Fixation

**Description**: Existing sessions are preserved during OAuth login, allowing session fixation attacks where attackers set a victim's session ID before authentication.

**Vulnerable Code**:
```python
# users/views/google_oauth.py - GoogleOAuthCallbackView
tokens = get_tokens_for_user(user)
response = Response(response_data, status=status.HTTP_200_OK)
set_refresh_cookie(response, tokens['refresh'])
# No session invalidation or regeneration
```

**Attack Scenario**:
1. Attacker obtains session ID and sets it in victim's browser
2. Victim logs in via Google OAuth
3. Session is preserved, attacker gains authenticated access
4. Attacker can access victim's account using the same session

**Impact**: Account takeover, unauthorized access to user data

**Mitigation Strategy**:
```python
# Enhanced callback with session security
def post(self, request):
    # ... existing OAuth processing ...
    
    # Invalidate any existing session
    if hasattr(request, 'session'):
        request.session.flush()  # Clear all session data
        request.session.cycle_key()  # Generate new session key
    
    # Generate new JWT tokens
    tokens = get_tokens_for_user(user)
    
    # Clear any existing auth cookies and set new ones
    response = Response(response_data, status=status.HTTP_200_OK)
    response.delete_cookie('refresh_token')  # Clear old cookie
    set_refresh_cookie(response, tokens['refresh'])
    
    return response
```

### 2. Medium Risk Vulnerabilities

#### 2.1 Authorization Code Reuse Vulnerability
**Severity**: Medium | **CVSS Score**: 5.4  
**CWE**: CWE-294 - Authentication Bypass by Capture-replay

**Description**: No tracking of used authorization codes could allow replay attacks if codes are intercepted.

**Vulnerable Code**:
```python
def exchange_code_for_tokens(self, code: str, redirect_uri: str):
    # No check if authorization code was already used
    response = requests.post(self.GOOGLE_TOKEN_URL, data=data)
```

**Attack Scenario**:
1. Attacker intercepts authorization code (HTTPS downgrade, network sniffing)
2. Victim uses code to authenticate successfully  
3. Attacker replays the same code later
4. If code hasn't expired, attacker could potentially authenticate

**Impact**: Unauthorized access, account compromise

**Mitigation Strategy**:
```python
class AuthorizationCodeTracker:
    """Track used authorization codes to prevent replay"""
    
    @staticmethod
    def is_code_used(code: str) -> bool:
        cache_key = f"oauth_code_used:{hashlib.sha256(code.encode()).hexdigest()}"
        return cache.get(cache_key) is not None
    
    @staticmethod
    def mark_code_used(code: str, ttl: int = 600):  # 10 minutes
        cache_key = f"oauth_code_used:{hashlib.sha256(code.encode()).hexdigest()}"
        cache.set(cache_key, timezone.now().isoformat(), timeout=ttl)

# Updated exchange method
def exchange_code_for_tokens(self, code: str, redirect_uri: str):
    # Check if code already used
    if AuthorizationCodeTracker.is_code_used(code):
        logger.warning(f"Authorization code reuse attempt detected")
        raise GoogleOAuthError("Authorization code has already been used")
    
    # Mark code as used before exchange
    AuthorizationCodeTracker.mark_code_used(code)
    
    # Proceed with token exchange
    response = requests.post(self.GOOGLE_TOKEN_URL, data=data)
    # ... rest of implementation
```

#### 2.2 OAuth State CSRF Bypass Vulnerability
**Severity**: Medium | **CVSS Score**: 5.9  
**CWE**: CWE-352 - Cross-Site Request Forgery (CSRF)

**Description**: IP address validation can be disabled, weakening CSRF protection for mobile applications.

**Vulnerable Code**:
```python
# Optional IP validation can be disabled
if getattr(settings, 'OAUTH_VALIDATE_IP', True) and state_data['ip_address'] != ip_address:
    raise GoogleOAuthError("OAuth state token used from different IP address")
```

**Attack Scenario**:
1. Attacker discovers IP validation is disabled
2. Attacker initiates OAuth flow and captures state token
3. Attacker tricks victim into visiting malicious page
4. Malicious page uses captured state token to complete OAuth

**Impact**: Account linking to attacker's Google account, unauthorized access

**Mitigation Strategy**:
```python
class EnhancedStateManager:
    """Enhanced OAuth state management with multiple validation layers"""
    
    @staticmethod
    def generate_state_token(request) -> Tuple[str, str]:
        """Generate state token with additional entropy"""
        base_token = secrets.token_urlsafe(32)
        
        # Add request-specific entropy
        request_data = f"{request.META.get('HTTP_USER_AGENT', '')}"
        entropy_hash = hashlib.sha256(request_data.encode()).hexdigest()[:8]
        
        full_token = f"{base_token}.{entropy_hash}"
        return full_token, entropy_hash
    
    @staticmethod
    def validate_enhanced_state(token: str, request, stored_data: dict) -> bool:
        """Validate state with multiple factors"""
        try:
            base_token, entropy_hash = token.split('.')
        except ValueError:
            return False
        
        # Validate request entropy
        request_data = f"{request.META.get('HTTP_USER_AGENT', '')}"
        expected_hash = hashlib.sha256(request_data.encode()).hexdigest()[:8]
        
        if entropy_hash != expected_hash:
            logger.warning("OAuth state entropy validation failed")
            return False
        
        # Additional validations
        if getattr(settings, 'OAUTH_VALIDATE_IP', True):
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            if stored_data['ip_address'] != client_ip:
                return False
        
        # Time-based validation
        created_at = datetime.fromisoformat(stored_data['created_at'])
        if timezone.now() - created_at > timedelta(seconds=300):  # 5 minutes
            return False
        
        return True
```

#### 2.3 Rate Limiting and DoS Vulnerabilities
**Severity**: Medium | **CVSS Score**: 5.0  
**CWE**: CWE-400 - Uncontrolled Resource Consumption

**Description**: Missing rate limiting on OAuth endpoints allows automated attacks and resource exhaustion.

**Vulnerable Endpoints**:
- `/auth/google/initiate/` - No rate limiting
- `/auth/google/callback/` - No rate limiting
- Email verification resend functionality

**Attack Scenario**:
1. Attacker scripts automated requests to OAuth initiation
2. Each request generates state tokens and cache entries
3. Redis cache fills up with OAuth state data
4. Legitimate users cannot initiate OAuth flows

**Impact**: Denial of service, resource exhaustion, service degradation

**Mitigation Strategy**:
```python
# users/throttles.py
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class GoogleOAuthInitiateThrottle(AnonRateThrottle):
    scope = 'oauth_initiate'
    
    def get_cache_key(self, request, view):
        # Rate limit by IP and User-Agent combination
        ip = request.META.get('REMOTE_ADDR', '')
        user_agent_hash = hashlib.sha256(
            request.META.get('HTTP_USER_AGENT', '').encode()
        ).hexdigest()[:8]
        
        return f"oauth_throttle_{ip}_{user_agent_hash}"

class GoogleOAuthCallbackThrottle(AnonRateThrottle):
    scope = 'oauth_callback'
    
class EmailResendThrottle(UserRateThrottle):
    scope = 'email_resend'

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'oauth_initiate': '10/hour',    # 10 OAuth initiations per hour per IP+UA
        'oauth_callback': '20/hour',    # 20 callbacks per hour per IP
        'email_resend': '5/hour',       # 5 email resends per hour per user
    }
}

# Apply to views
class GoogleOAuthInitiateView(APIView):
    throttle_classes = [GoogleOAuthInitiateThrottle]
    
class GoogleOAuthCallbackView(APIView):
    throttle_classes = [GoogleOAuthCallbackThrottle]
```

#### 2.4 Google ID Format Validation Vulnerability
**Severity**: Medium | **CVSS Score**: 4.7  
**CWE**: CWE-20 - Improper Input Validation

**Description**: Direct assignment of Google ID without format validation could cause data integrity issues.

**Vulnerable Code**:
```python
# Direct assignment without validation
user.google_id = google_user_info['sub']
```

**Attack Scenario**:
1. Attacker manipulates Google OAuth response (MITM, DNS poisoning)
2. Malicious response contains invalid Google ID format
3. Invalid data stored in database
4. Potential SQL injection or data corruption issues

**Impact**: Data integrity compromise, potential injection attacks

**Mitigation Strategy**:
```python
import re

class GoogleDataValidator:
    """Validate Google OAuth response data"""
    
    # Google ID is numeric string, typically 21 digits
    GOOGLE_ID_PATTERN = re.compile(r'^\d{10,30}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    @classmethod
    def validate_google_user_info(cls, user_info: dict) -> dict:
        """Validate and sanitize Google user info"""
        validated = {}
        
        # Validate Google ID (sub)
        google_id = user_info.get('sub', '')
        if not cls.GOOGLE_ID_PATTERN.match(google_id):
            raise GoogleTokenValidationError(f"Invalid Google ID format: {google_id}")
        validated['sub'] = google_id
        
        # Validate email
        email = user_info.get('email', '').lower()
        if not cls.EMAIL_PATTERN.match(email):
            raise GoogleTokenValidationError(f"Invalid email format: {email}")
        validated['email'] = email
        
        # Validate names (sanitize)
        for field in ['given_name', 'family_name', 'name']:
            if field in user_info:
                value = user_info[field][:100]  # Limit length
                # Remove potentially dangerous characters
                sanitized = re.sub(r'[<>"\']', '', value)
                validated[field] = sanitized
        
        # Copy other safe fields
        for field in ['email_verified', 'picture']:
            if field in user_info:
                validated[field] = user_info[field]
        
        return validated

# Updated service method
def validate_id_token(self, id_token_str: str) -> Dict[str, Any]:
    """Validate Google ID token and extract user info"""
    try:
        # Existing validation
        idinfo = id_token.verify_oauth2_token(
            id_token_str, 
            google_requests.Request(), 
            self.client_id
        )
        
        # Additional validation
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise GoogleTokenValidationError('Invalid token issuer')
        
        # Validate and sanitize user info
        validated_info = GoogleDataValidator.validate_google_user_info(idinfo)
        
        return validated_info
    except ValueError as e:
        raise GoogleTokenValidationError(f"Invalid ID token: {e}")
```

#### 2.5 Information Disclosure Vulnerability
**Severity**: Medium | **CVSS Score**: 4.3  
**CWE**: CWE-209 - Generation of Error Message Containing Sensitive Information

**Description**: Error messages may leak sensitive information from Google API responses.

**Vulnerable Code**:
```python
# Potential information leakage in error messages
raise GoogleOAuthError(f"Failed to get user info: {response.text}")
raise GoogleTokenValidationError(f"Failed to exchange code for tokens: {response.text}")
```

**Attack Scenario**:
1. Attacker triggers various error conditions
2. Detailed error messages reveal internal system information
3. Information used to craft more targeted attacks

**Impact**: Information disclosure, system reconnaissance

**Mitigation Strategy**:
```python
class SecureErrorHandler:
    """Handle errors without information disclosure"""
    
    @staticmethod
    def sanitize_error_message(error_msg: str, response_text: str = None) -> str:
        """Generate user-safe error message"""
        # Log detailed error for debugging
        logger.error(f"OAuth Error Details: {error_msg}", extra={
            'response_text': response_text,
            'error_type': 'oauth_error'
        })
        
        # Return generic user message
        if "token" in error_msg.lower():
            return "Invalid authentication token. Please try again."
        elif "user info" in error_msg.lower():
            return "Unable to retrieve user information. Please try again."
        elif "exchange" in error_msg.lower():
            return "Authentication failed. Please try again."
        else:
            return "An authentication error occurred. Please try again."

# Updated error handling
def exchange_code_for_tokens(self, code: str, redirect_uri: str):
    try:
        response = requests.post(self.GOOGLE_TOKEN_URL, data=data)
        
        if response.status_code != 200:
            # Log detailed error, return generic message
            error_msg = SecureErrorHandler.sanitize_error_message(
                f"Token exchange failed with status {response.status_code}",
                response.text
            )
            raise GoogleTokenValidationError(error_msg)
            
    except requests.RequestException as e:
        error_msg = SecureErrorHandler.sanitize_error_message(
            f"Network error during token exchange: {e}"
        )
        raise GoogleTokenValidationError(error_msg)
```

### 3. Low Risk Vulnerabilities

#### 3.1 Username Enumeration Timing Attack
**Severity**: Low | **CVSS Score**: 3.1  
**CWE**: CWE-208 - Observable Timing Discrepancy

**Description**: Username generation timing differences could reveal existing usernames.

**Mitigation Strategy**:
```python
def generate_unique_username(self, google_user_info: Dict[str, Any]) -> str:
    """Generate username with constant timing"""
    base_username = google_user_info.get('email', '').split('@')[0]
    base_username = ''.join(c for c in base_username if c.isalnum() or c in '._-')
    
    if not base_username:
        base_username = f"google_user_{google_user_info['sub'][:8]}"
    
    # Use a more predictable approach to avoid timing attacks
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    username = f"{base_username}_{unique_suffix}"
    
    # Ensure uniqueness with minimal database queries
    max_attempts = 5
    for attempt in range(max_attempts):
        if not User.objects.filter(username=username).exists():
            return username
        username = f"{base_username}_{unique_suffix}_{attempt}"
    
    # Fallback to UUID-based username
    return f"user_{str(uuid.uuid4()).replace('-', '')[:12]}"
```

#### 3.2 Email Existence Timing Attack
**Severity**: Low | **CVSS Score**: 2.8  
**CWE**: CWE-208 - Observable Timing Discrepancy

**Description**: Different processing times could reveal email existence.

**Mitigation Strategy**:
```python
def find_or_create_user(self, google_user_info: Dict[str, Any]) -> Tuple[User, str]:
    """Find user with constant timing"""
    google_email = google_user_info['email']
    
    # Always perform both queries to maintain constant timing
    google_user = User.objects.filter(google_id=google_user_info['sub']).first()
    email_user = User.objects.filter(email=google_email).first()
    
    if google_user:
        google_user.update_from_google(google_user_info)
        return google_user, 'authenticated'
    
    if email_user:
        if not email_user.email_verified:
            # Add artificial delay to match creation timing
            import time
            time.sleep(0.1)
            
            logger.warning("OAuth blocked for unverified account")
            raise GoogleOAuthError("Email verification required")
        
        return self.link_google_to_existing_user(email_user, google_user_info)
    
    # Add consistent delay before user creation
    import time
    time.sleep(0.1)
    
    return self.create_google_user(google_user_info)
```

#### 3.3 Cache Key Enumeration Vulnerability
**Severity**: Low | **CVSS Score**: 2.4  
**CWE**: CWE-330 - Use of Insufficiently Random Values

**Description**: Predictable cache keys could allow enumeration if Redis is compromised.

**Mitigation Strategy**:
```python
class SecureCacheManager:
    """Secure cache key management"""
    
    @staticmethod
    def generate_cache_key(prefix: str, identifier: str) -> str:
        """Generate obfuscated cache key"""
        # Add application secret to prevent enumeration
        secret_key = settings.SECRET_KEY[:16]
        combined = f"{prefix}:{identifier}:{secret_key}"
        
        # Hash to obfuscate the actual identifier
        key_hash = hashlib.sha256(combined.encode()).hexdigest()
        return f"oauth:{key_hash[:32]}"
    
    @staticmethod
    def store_oauth_state(token: str, data: dict, ip_address: str):
        """Store OAuth state with secure cache key"""
        cache_key = SecureCacheManager.generate_cache_key("state", token)
        cache_data = {
            'data': data,
            'ip_address': ip_address,
            'created_at': timezone.now().isoformat()
        }
        cache.set(cache_key, cache_data, timeout=300)
```

#### 3.4 Token Replay Protection
**Severity**: Low | **CVSS Score**: 3.7  
**CWE**: CWE-294 - Authentication Bypass by Capture-replay

**Description**: Additional protection against ID token replay attacks.

**Mitigation Strategy**:
```python
def validate_id_token(self, id_token_str: str) -> Dict[str, Any]:
    """Enhanced ID token validation with replay protection"""
    try:
        # Standard validation
        idinfo = id_token.verify_oauth2_token(
            id_token_str, 
            google_requests.Request(), 
            self.client_id
        )
        
        # Additional timestamp validation
        issued_at = idinfo.get('iat')
        current_time = int(timezone.now().timestamp())
        
        # Reject tokens older than 5 minutes
        if current_time - issued_at > 300:
            raise GoogleTokenValidationError("ID token is too old")
        
        # Check for token reuse
        token_hash = hashlib.sha256(id_token_str.encode()).hexdigest()
        cache_key = f"oauth_token_used:{token_hash}"
        
        if cache.get(cache_key):
            raise GoogleTokenValidationError("ID token has already been used")
        
        # Mark token as used (cache for longer than token lifetime)
        cache.set(cache_key, True, timeout=3600)  # 1 hour
        
        return GoogleDataValidator.validate_google_user_info(idinfo)
        
    except ValueError as e:
        raise GoogleTokenValidationError(f"Invalid ID token: {e}")
```

## Implementation Priority Matrix

### Immediate Implementation (High Priority)
1. **Redirect URI Validation** - Critical for preventing phishing attacks
2. **Session Security** - Essential for preventing session fixation
3. **Rate Limiting** - Important for service availability
4. **Authorization Code Tracking** - Prevent replay attacks

### Next Phase (Medium Priority)
5. **Enhanced State Management** - Strengthen CSRF protection
6. **Input Validation** - Improve data integrity
7. **Error Message Security** - Reduce information disclosure

### Long Term (Low Priority)  
8. **Timing Attack Mitigation** - Reduce information leakage
9. **Cache Security** - Defense in depth
10. **Token Replay Protection** - Additional security layer

## Security Monitoring and Alerting

### Critical Security Events to Monitor
```python
# High priority security alerts
CRITICAL_SECURITY_EVENTS = [
    'oauth_redirect_uri_violation',
    'oauth_code_reuse_attempt', 
    'oauth_state_token_abuse',
    'oauth_rate_limit_exceeded',
    'oauth_session_fixation_attempt'
]

# Medium priority security events
SECURITY_EVENTS = [
    'oauth_invalid_google_id_format',
    'oauth_timing_attack_detected',
    'oauth_token_replay_attempt',
    'oauth_blocked_unverified_account'
]
```

### Automated Response Actions
```python
def trigger_security_response(event_type: str, context: dict):
    """Automated security response based on event type"""
    
    if event_type in CRITICAL_SECURITY_EVENTS:
        # Immediate blocking and alerts
        alert_security_team(event_type, context)
        
        if event_type == 'oauth_rate_limit_exceeded':
            block_ip_temporarily(context['ip_address'], duration=3600)
        
        elif event_type == 'oauth_code_reuse_attempt':
            revoke_user_tokens(context.get('user_id'))
    
    # Log all security events for analysis
    security_logger.warning(f"OAuth Security Event: {event_type}", extra=context)
```

## Testing and Validation

### Security Test Cases
```python
class OAuthSecurityTests(TestCase):
    """Comprehensive security testing for OAuth implementation"""
    
    def test_redirect_uri_validation(self):
        """Test redirect URI whitelist validation"""
        # Test malicious redirect URIs
        malicious_uris = [
            'https://evil.com/steal-tokens',
            'javascript:alert(1)',
            'data:text/html,<script>alert(1)</script>',
            'https://legitimate-site.com.evil.com/',
        ]
        
        for uri in malicious_uris:
            with self.assertRaises(ValidationError):
                validate_redirect_uri(uri)
    
    def test_authorization_code_reuse_prevention(self):
        """Test authorization code can only be used once"""
        code = "test_auth_code"
        
        # First use should succeed
        service = GoogleOAuthService()
        # ... mock successful exchange ...
        
        # Second use should fail
        with self.assertRaises(GoogleOAuthError):
            service.exchange_code_for_tokens(code, "https://test.com/callback")
    
    def test_rate_limiting_enforcement(self):
        """Test rate limiting prevents abuse"""
        client = APIClient()
        
        # Exceed rate limit
        for i in range(15):  # Limit is 10/hour
            response = client.post('/api/auth/google/initiate/', {
                'redirect_uri': 'https://test.com/callback'
            })
        
        # Should be rate limited
        self.assertEqual(response.status_code, 429)
    
    def test_session_security(self):
        """Test session fixation prevention"""
        # Set initial session
        session = self.client.session
        initial_key = session.session_key
        
        # Complete OAuth flow
        # ... OAuth callback simulation ...
        
        # Session key should change
        new_session = self.client.session
        self.assertNotEqual(initial_key, new_session.session_key)
```

## Conclusion

This security analysis identifies 11 potential vulnerabilities ranging from critical (open redirect) to low impact (timing attacks). The recommended implementation priority focuses on the most impactful security issues that could lead to account takeover or service disruption.

Key security improvements include:
- **Redirect URI validation** to prevent phishing
- **Session security** to prevent fixation attacks  
- **Enhanced rate limiting** to prevent DoS
- **Input validation** to ensure data integrity
- **Comprehensive monitoring** for threat detection

Implementation of these security measures will significantly strengthen the OAuth integration against common attack vectors and provide a robust security posture for user authentication.