# Epic 3: Google OAuth Security Hardening

**Epic ID**: OAUTH-003  
**Status**: Blocked (depends on OAUTH-002)  
**Priority**: P0 - Critical (Security)  
**Sprint**: Sprint 2, Week 1  
**Estimated Effort**: 5 story points  
**Dependencies**: OAUTH-002 (API Implementation)  
**Related ADR**: [ADR-010: Google OAuth Integration](../architecture/adr/ADR-010-GOOGLE-OAUTH-INTEGRATION.md)

---

## Epic Goal

Implement comprehensive security measures for OAuth integration including rate limiting, PKCE enforcement, security monitoring, audit logging, and penetration testing. This epic ensures the OAuth implementation meets enterprise security standards.

---

## Business Value

- Prevents account takeover attacks
- Protects against OAuth vulnerabilities (CSRF, replay, open redirect)
- Enables security compliance and audit requirements
- Builds customer trust with secure authentication

---

## User Stories

### Story 3.1: Rate Limiting Implementation
**As a** security engineer  
**I want** rate limiting on OAuth endpoints  
**So that** automated attacks are prevented

**Acceptance Criteria:**
1. OAuth initiate endpoint limited to 5 requests/15 min per IP
2. OAuth callback endpoint limited to 10 requests/15 min per IP
3. Rate limits enforced using Django REST Framework throttling
4. Rate limit exceeded returns 429 status with retry-after header
5. Rate limits configurable via settings

**Technical Notes:**
```python
# auth/throttles.py
from rest_framework.throttling import AnonRateThrottle

class OAuthInitiateThrottle(AnonRateThrottle):
    scope = 'oauth_initiate'
    
    def get_cache_key(self, request, view):
        # Use IP address for anonymous rate limiting
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }

class OAuthCallbackThrottle(AnonRateThrottle):
    scope = 'oauth_callback'

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'oauth_initiate': '5/15m',
        'oauth_callback': '10/15m',
    }
}
```

**Definition of Done:**
- [ ] Throttle classes created
- [ ] Applied to OAuth views
- [ ] Returns 429 with proper headers
- [ ] Configurable via settings
- [ ] Integration tests verify limits
- [ ] Monitoring alerts configured

---

### Story 3.2: PKCE Enforcement
**As a** security engineer  
**I want** PKCE required for all OAuth flows  
**So that** authorization code interception is prevented

**Acceptance Criteria:**
1. Code verifier generated for every OAuth initiation
2. Code challenge included in Google OAuth URL
3. Code verifier validated during callback
4. Missing or invalid PKCE fails with clear error
5. PKCE implementation follows RFC 7636

**Technical Notes:**
- Use SHA256 for code challenge method
- Code verifier: 43-128 characters, base64url encoded
- Store code_verifier in GoogleOAuthState
- Validate in `exchange_code_for_token()`

**PKCE Flow:**
```python
# During initiate
code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode('utf-8')).digest()
).decode('utf-8').rstrip('=')

# During callback
if stored_verifier != received_verifier:
    raise PKCEVerificationError("Code verifier mismatch")
```

**Definition of Done:**
- [ ] PKCE generation implemented
- [ ] Code challenge in OAuth URL
- [ ] Verification in callback works
- [ ] Tests for valid/invalid PKCE
- [ ] Error messages helpful

---

### Story 3.3: Redirect URI Whitelist Validation
**As a** security engineer  
**I want** strict redirect URI validation  
**So that** open redirect attacks are prevented

**Acceptance Criteria:**
1. Redirect URIs validated against whitelist
2. Exact match required (no partial matches)
3. Scheme, host, and path all validated
4. Invalid URIs rejected with 400 error
5. Whitelist configurable per environment

**Technical Notes:**
```python
# auth/validators.py
from urllib.parse import urlparse

class RedirectURIValidator:
    @staticmethod
    def validate(redirect_uri: str) -> bool:
        """Validate redirect URI against whitelist"""
        allowed = settings.OAUTH_ALLOWED_REDIRECT_URIS
        
        try:
            parsed = urlparse(redirect_uri)
            
            for allowed_uri in allowed:
                allowed_parsed = urlparse(allowed_uri)
                
                # Exact match for scheme, host, path prefix
                if (parsed.scheme == allowed_parsed.scheme and
                    parsed.netloc == allowed_parsed.netloc and
                    parsed.path.startswith(allowed_parsed.path)):
                    return True
            
            return False
        except Exception:
            return False
```

**Definition of Done:**
- [ ] Validator class created
- [ ] Whitelist from settings
- [ ] Rejects invalid URIs
- [ ] Unit tests for edge cases
- [ ] Logging for rejected attempts

---

### Story 3.4: Security Audit Logging
**As a** security analyst  
**I want** all OAuth events logged  
**So that** security incidents can be investigated

**Acceptance Criteria:**
1. All OAuth attempts logged with IP, user agent, timestamp
2. Security blocks logged (unverified accounts, invalid state)
3. Rate limit triggers logged
4. Successful authentications logged
5. Logs structured and searchable

**Log Events:**
- `oauth.initiate` - OAuth flow started
- `oauth.callback.success` - User authenticated
- `oauth.callback.failure` - Authentication failed
- `oauth.security_block` - Security rule triggered
- `oauth.account_created` - New account via OAuth
- `oauth.account_linked` - Google linked to existing account
- `oauth.rate_limit_exceeded` - Too many requests

**Technical Notes:**
```python
# Use structured logging
import logging

logger = logging.getLogger('oauth.security')

logger.info('OAuth flow initiated', extra={
    'event': 'oauth.initiate',
    'ip_address': request_ip,
    'user_agent': request.META.get('HTTP_USER_AGENT'),
    'redirect_uri': redirect_uri,
    'timestamp': timezone.now().isoformat(),
})

logger.warning('OAuth blocked: unverified account', extra={
    'event': 'oauth.security_block',
    'reason': 'unverified_account',
    'email': user_email,
    'google_id': google_id,
    'ip_address': request_ip,
})
```

**Definition of Done:**
- [ ] Logging implemented for all events
- [ ] Structured log format
- [ ] Log aggregation configured
- [ ] Security dashboard created
- [ ] Alert rules configured

---

### Story 3.5: OAuth State Security
**As a** security engineer  
**I want** OAuth state tokens to be cryptographically secure  
**So that** CSRF attacks are prevented

**Acceptance Criteria:**
1. State tokens are 128+ characters, cryptographically random
2. Nonce included in state for additional CSRF protection
3. State includes timestamp for expiration validation
4. State tokens stored securely (hashed if needed)
5. Used tokens immediately invalidated

**Technical Notes:**
```python
import secrets
import hashlib

def generate_state_token():
    """Generate cryptographically secure state token"""
    random_bytes = secrets.token_bytes(64)
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(32)
    
    combined = f"{random_bytes.hex()}{timestamp}{nonce}"
    state_token = hashlib.sha512(combined.encode()).hexdigest()
    
    return state_token, nonce

def validate_state_token(state_token, stored_token, nonce):
    """Constant-time comparison to prevent timing attacks"""
    return secrets.compare_digest(state_token, stored_token)
```

**Definition of Done:**
- [ ] State generation cryptographically secure
- [ ] Nonce implementation working
- [ ] Constant-time comparison used
- [ ] Expiration enforced
- [ ] Used tokens cannot be reused

---

### Story 3.6: Security Penetration Testing
**As a** security engineer  
**I want** OAuth implementation penetration tested  
**So that** vulnerabilities are identified before production

**Test Scenarios:**
1. **CSRF Attack**: Attempt OAuth with forged state token
2. **Open Redirect**: Try malicious redirect URIs
3. **Session Fixation**: Attempt to fixate session during OAuth
4. **Code Replay**: Reuse authorization codes
5. **State Replay**: Reuse state tokens
6. **Timing Attack**: Measure response times for token validation
7. **Rate Limit Bypass**: Attempt to circumvent rate limiting
8. **Account Takeover**: Try linking to unverified accounts

**Testing Tools:**
- OWASP ZAP for automated scanning
- Burp Suite for manual testing
- Custom scripts for OAuth-specific attacks

**Definition of Done:**
- [ ] All 8 attack scenarios tested
- [ ] Vulnerabilities documented
- [ ] Critical issues fixed
- [ ] Medium/low issues tracked
- [ ] Penetration test report created

---

## Epic Acceptance Criteria

This epic is complete when:
- [ ] All 6 stories completed
- [ ] Rate limiting enforced and tested
- [ ] PKCE implementation verified
- [ ] Redirect URI validation prevents open redirects
- [ ] Security logging captures all events
- [ ] Penetration testing shows no critical vulnerabilities
- [ ] Security sign-off obtained

---

## Security Testing Checklist

From OWASP OAuth 2.0 Threat Model (RFC 6819):

- [ ] Authorization code can only be used once
- [ ] State parameter validated (CSRF protection)
- [ ] Redirect URI strictly validated
- [ ] PKCE code challenge verified
- [ ] Token expiration enforced
- [ ] No secrets in URLs or logs
- [ ] Rate limiting prevents brute force
- [ ] Timing attacks mitigated (constant-time comparison)
- [ ] Session management secure
- [ ] Email verification prevents account takeover

---

## Monitoring & Alerting

### Metrics to Track
- OAuth success/failure rate
- Rate limit triggers per hour
- Security blocks per day
- Average OAuth completion time
- Google API error rate

### Alerts to Configure
- High failure rate (>10% for 5 minutes)
- Spike in security blocks (>50 in 1 hour)
- Rate limit abuse from single IP (>100 triggers/hour)
- Google API errors (>5% error rate)

---

## Documentation Updates

- [ ] Security architecture document
- [ ] Incident response runbook for OAuth
- [ ] Security monitoring dashboard setup
- [ ] Penetration test report
- [ ] Security sign-off checklist

---

## Dependencies & Blockers

**Upstream Dependencies:**
- OAUTH-002: API Implementation (MUST be complete)

**Blocks:**
- OAUTH-004: Frontend Integration (shouldn't start without security)
- Production deployment (cannot deploy without security sign-off)

---

## Success Metrics

- Zero critical vulnerabilities found in penetration testing
- Rate limiting blocks automated attacks (>95% effective)
- OAuth security events logged and monitored
- Security team sign-off obtained

---

**Epic Owner**: Security Team Lead  
**Stakeholders**: Security Team, Backend Developers, DevOps  
**Target Completion**: End of Sprint 2, Week 1

