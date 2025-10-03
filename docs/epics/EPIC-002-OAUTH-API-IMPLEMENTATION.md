# Epic 2: Google OAuth API Implementation

**Epic ID**: OAUTH-002  
**Status**: Blocked (depends on OAUTH-001)  
**Priority**: P0 - Critical Path  
**Sprint**: Sprint 1, Week 2  
**Estimated Effort**: 8 story points  
**Dependencies**: OAUTH-001 (Backend Infrastructure)  
**Related ADR**: [ADR-010: Google OAuth Integration](../architecture/adr/ADR-010-GOOGLE-OAUTH-INTEGRATION.md)

---

## Epic Goal

Implement the core Google OAuth API endpoints and business logic, enabling users to initiate OAuth flow, handle Google's callback, and receive JWT tokens. This epic delivers the functional OAuth integration that other components will consume.

---

## Business Value

- Enables "Sign in with Google" button functionality
- Reduces signup time from 3 steps to 1 click
- Automatic email verification for Google users
- Foundation for account linking features

---

## User Stories

### Story 2.1: Google OAuth Service Class
**As a** backend developer  
**I want** a reusable OAuth service class  
**So that** OAuth logic is centralized and testable

**Acceptance Criteria:**
1. `GoogleOAuthService` class created with methods for all OAuth operations
2. Methods include: `generate_auth_url()`, `validate_state()`, `exchange_code_for_token()`, `get_user_info()`, `get_or_create_user()`
3. Service handles PKCE (code challenge/verifier)
4. Service validates redirect URIs against whitelist
5. All methods have comprehensive error handling

**Technical Notes:**
```python
# auth/services/google_oauth_service.py

class GoogleOAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        self.client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
        self.scopes = settings.GOOGLE_OAUTH_SCOPES
    
    def generate_auth_url(self, state_token, code_verifier):
        """Generate Google OAuth URL with PKCE"""
        # Implementation
    
    def validate_state_token(self, state_token, ip_address):
        """Validate OAuth state token"""
        # Check expiration, used_at, IP match
    
    def exchange_code_for_token(self, code, code_verifier, state_token):
        """Exchange authorization code for access token"""
        # Call Google API with PKCE
    
    def get_user_info(self, access_token):
        """Get user info from Google"""
        # Call Google UserInfo API
    
    def get_or_create_user(self, google_user_info):
        """Get existing user or create new Google-authenticated user"""
        # Implements 5 account scenarios from ADR
```

**Definition of Done:**
- [ ] Service class created with all methods
- [ ] PKCE implementation verified
- [ ] Redirect URI validation works
- [ ] Error handling comprehensive
- [ ] Unit tests for all methods (90%+ coverage)

---

### Story 2.2: OAuth Initiate Endpoint
**As a** frontend developer  
**I want** an endpoint to start OAuth flow  
**So that** I can redirect users to Google sign-in

**API Endpoint:** `POST /api/auth/google/initiate/`

**Acceptance Criteria:**
1. Endpoint generates OAuth state token with PKCE
2. State token stored in Redis/DB with 10-minute expiration
3. Returns Google OAuth URL for frontend to redirect to
4. Validates redirect_uri against whitelist
5. Rate limited to 5 requests per 15 minutes per IP

**Request:**
```json
{
  "redirect_uri": "https://tinybeans.app/auth/google/callback"
}
```

**Response (200 OK):**
```json
{
  "google_oauth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&state=...&code_challenge=...",
  "state": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 600
}
```

**Response (400 Bad Request):**
```json
{
  "error": {
    "code": "INVALID_REDIRECT_URI",
    "message": "Redirect URI not in whitelist"
  }
}
```

**Technical Notes:**
- View: `auth/views/google_oauth.py::GoogleOAuthInitiateView`
- Generate cryptographically secure state token (128 chars)
- Generate PKCE code_verifier and code_challenge
- Store in GoogleOAuthState model
- Log initiation attempts for security monitoring

**Definition of Done:**
- [ ] Endpoint implemented and tested
- [ ] State token generation secure
- [ ] Rate limiting enforced
- [ ] Whitelist validation works
- [ ] Returns valid Google OAuth URL
- [ ] Integration test passes

---

### Story 2.3: OAuth Callback Endpoint
**As a** user  
**I want** to complete Google sign-in  
**So that** I can access my account

**API Endpoint:** `POST /api/auth/google/callback/`

**Acceptance Criteria:**
1. Endpoint exchanges authorization code for Google access token
2. Validates OAuth state token (not expired, not used, matches IP)
3. Gets user info from Google
4. Implements 5 account scenarios (new user, existing verified, existing unverified, etc.)
5. Returns JWT access and refresh tokens
6. Marks state token as used

**Request:**
```json
{
  "code": "4/0AeanSxW7uOuK...",
  "state": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK - New User):**
```json
{
  "user": {
    "id": 42,
    "email": "user@gmail.com",
    "username": "user_12345",
    "first_name": "John",
    "last_name": "Doe",
    "auth_provider": "google",
    "google_id": "106839298367298367",
    "email_verified": true
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "account_action": "created"
}
```

**Response (200 OK - Existing User Linked):**
```json
{
  "user": {...},
  "tokens": {...},
  "account_action": "linked"
}
```

**Response (403 Forbidden - Unverified Account):**
```json
{
  "error": {
    "code": "UNVERIFIED_ACCOUNT_EXISTS",
    "message": "An unverified account exists with this email. Please verify your email first.",
    "email": "user@gmail.com",
    "help_url": "/help/verify-email"
  }
}
```

**Technical Notes:**
- View: `auth/views/google_oauth.py::GoogleOAuthCallbackView`
- Use `GoogleOAuthService.exchange_code_for_token()` with PKCE
- Implement account linking security check (email_verified requirement)
- Generate JWT tokens using existing token generator
- Set refresh token in HTTP-only cookie
- Log all OAuth completions (success, failure, blocked)

**5 Account Scenarios to Handle:**
1. New user → Create account, set email_verified=True
2. Existing verified user → Link Google ID, set auth_provider='hybrid'
3. Existing unverified user → BLOCK with 403 error
4. User with existing Google ID → Login (return tokens)
5. Multiple Google accounts same email → Use google_id as primary identifier

**Definition of Done:**
- [ ] Endpoint implemented with all 5 scenarios
- [ ] PKCE verification works
- [ ] State validation enforced
- [ ] JWT tokens issued correctly
- [ ] HTTP-only cookies set
- [ ] Comprehensive integration tests
- [ ] Security scenarios tested

---

### Story 2.4: OAuth Account Linking Endpoint
**As an** authenticated user  
**I want** to link my Google account  
**So that** I can use Google sign-in in the future

**API Endpoint:** `POST /api/auth/google/link/`

**Acceptance Criteria:**
1. Endpoint requires authentication (JWT token)
2. Links Google account to authenticated user
3. Validates Google email matches user's email
4. Updates auth_provider to 'hybrid'
5. Prevents linking if already linked to different account

**Request:**
```http
POST /api/auth/google/link/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
  "code": "4/0AeanSxW7uOuK...",
  "state": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "message": "Google account linked successfully",
  "user": {
    "id": 42,
    "email": "user@example.com",
    "auth_provider": "hybrid",
    "google_id": "106839298367298367",
    "google_linked_at": "2025-01-12T15:30:00Z"
  }
}
```

**Response (409 Conflict):**
```json
{
  "error": {
    "code": "GOOGLE_ACCOUNT_ALREADY_LINKED",
    "message": "This Google account is already linked to another user"
  }
}
```

**Technical Notes:**
- View: `auth/views/google_oauth.py::GoogleOAuthLinkView`
- Requires `IsAuthenticated` permission
- Validate Google email matches user's email
- Check if google_id already exists in database
- Update user model fields atomically
- Log linking events for audit

**Definition of Done:**
- [ ] Endpoint implemented and authenticated
- [ ] Email matching validated
- [ ] Prevents duplicate linking
- [ ] Updates user model correctly
- [ ] Audit logging implemented
- [ ] Integration tests pass

---

### Story 2.5: OAuth Account Unlinking Endpoint
**As an** authenticated user  
**I want** to unlink my Google account  
**So that** I can use only password authentication

**API Endpoint:** `DELETE /api/auth/google/unlink/`

**Acceptance Criteria:**
1. Endpoint requires authentication
2. Requires password confirmation for security
3. Removes Google ID from user account
4. Updates auth_provider to 'manual'
5. Only allows unlinking if user has usable password

**Request:**
```http
DELETE /api/auth/google/unlink/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
  "password": "user_password"
}
```

**Response (200 OK):**
```json
{
  "message": "Google account unlinked successfully",
  "user": {
    "id": 42,
    "auth_provider": "manual",
    "google_id": null,
    "has_usable_password": true
  }
}
```

**Response (400 Bad Request - No Password):**
```json
{
  "error": {
    "code": "CANNOT_UNLINK_WITHOUT_PASSWORD",
    "message": "You must set a password before unlinking Google account",
    "help_url": "/help/set-password"
  }
}
```

**Technical Notes:**
- View: `auth/views/google_oauth.py::GoogleOAuthUnlinkView`
- Verify password before unlinking (security)
- Check `has_usable_password` is True
- Set google_id to None, google_email to None
- Update auth_provider based on remaining methods
- Log unlinking events

**Definition of Done:**
- [ ] Endpoint implemented
- [ ] Password verification works
- [ ] Prevents unlinking without password
- [ ] Updates user model correctly
- [ ] Audit logging implemented
- [ ] Edge cases tested

---

### Story 2.6: OAuth Serializers
**As a** backend developer  
**I want** DRF serializers for OAuth requests/responses  
**So that** validation and documentation are consistent

**Acceptance Criteria:**
1. Serializers for all OAuth endpoints created
2. Input validation for all required fields
3. Output serializers match API documentation
4. Error serializers provide helpful messages
5. Serializers generate OpenAPI schema correctly

**Technical Notes:**
```python
# auth/serializers/oauth_serializers.py

class OAuthInitiateRequestSerializer(serializers.Serializer):
    redirect_uri = serializers.URLField(required=True)

class OAuthInitiateResponseSerializer(serializers.Serializer):
    google_oauth_url = serializers.URLField()
    state = serializers.CharField()
    expires_in = serializers.IntegerField()

class OAuthCallbackRequestSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, max_length=512)
    state = serializers.CharField(required=True, max_length=512)

class OAuthCallbackResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    tokens = JWTTokenSerializer()
    account_action = serializers.ChoiceField(
        choices=['created', 'linked', 'login']
    )

# ... more serializers
```

**Definition of Done:**
- [ ] All serializers created
- [ ] Validation rules match requirements
- [ ] Serializers tested with valid/invalid data
- [ ] OpenAPI schema generation verified
- [ ] Documentation matches implementation

---

## Epic Acceptance Criteria

This epic is complete when:
- [ ] All 6 stories completed and merged
- [ ] OAuth flow works end-to-end (initiate → callback → JWT tokens)
- [ ] All 5 account scenarios tested and working
- [ ] Rate limiting enforced on all endpoints
- [ ] Integration tests pass for complete OAuth flow
- [ ] API documentation updated

---

## Testing Requirements

### Unit Tests
- GoogleOAuthService methods (each method tested)
- State token generation and validation
- PKCE code challenge/verifier
- Account linking logic (all 5 scenarios)
- Serializer validation

### Integration Tests
- Complete OAuth flow (initiate → callback)
- Account creation via OAuth
- Account linking for existing users
- Unverified account blocking
- Rate limiting enforcement

### Manual Testing
- OAuth flow in browser
- Google sign-in UI
- Error messages display correctly
- Tokens work for protected endpoints

---

## Security Testing

- [ ] State token replay attack prevented
- [ ] Expired state tokens rejected
- [ ] Invalid redirect URI rejected
- [ ] Email verification check prevents account takeover
- [ ] Rate limiting prevents brute force
- [ ] CSRF protection via state parameter

---

## Documentation Updates

- [ ] Update API docs with OAuth endpoints
- [ ] Add code examples for each endpoint
- [ ] Document error codes and responses
- [ ] Update Postman collection
- [ ] Create developer integration guide

---

## Dependencies & Blockers

**Upstream Dependencies:**
- OAUTH-001: Backend Infrastructure (MUST be complete)

**Blocks:**
- OAUTH-003: Security Hardening
- OAUTH-004: Frontend Integration

---

## Success Metrics

- OAuth callback completes in < 500ms (p95)
- 95%+ success rate for valid OAuth attempts
- Zero account takeover incidents
- < 1% error rate for OAuth flow

---

**Epic Owner**: Backend Team Lead  
**Stakeholders**: Backend Developers, Frontend Team, QA  
**Target Completion**: End of Sprint 1, Week 2

