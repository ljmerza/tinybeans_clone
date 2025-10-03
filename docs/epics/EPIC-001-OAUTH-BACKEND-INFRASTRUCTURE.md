# Epic 1: Google OAuth Backend Infrastructure

**Epic ID**: OAUTH-001  
**Status**: Ready for Development  
**Priority**: P0 - Critical Path  
**Sprint**: Sprint 1, Week 1  
**Estimated Effort**: 5 story points  
**Dependencies**: None  
**Related ADR**: [ADR-010: Google OAuth Integration](../architecture/adr/ADR-010-GOOGLE-OAUTH-INTEGRATION.md)

---

## Epic Goal

Establish the foundational backend infrastructure for Google OAuth integration, including database schema changes, OAuth state management, and environment configuration. This epic sets up the technical foundation that all subsequent OAuth features will build upon.

---

## Business Value

- Enables "Sign in with Google" feature to reduce signup friction
- Reduces support burden by eliminating email verification step for Google users
- Positions Tinybeans for multi-provider OAuth support (Apple, Microsoft)
- Improves security with enterprise-grade OAuth 2.0 implementation

---

## User Stories

### Story 1.1: Database Schema for OAuth Support
**As a** backend developer  
**I want** to add Google OAuth fields to the User model  
**So that** users can authenticate with Google and link accounts

**Acceptance Criteria:**
1. User model has new fields: `google_id`, `google_email`, `has_usable_password`, `auth_provider`, `google_linked_at`, `last_google_sync`
2. All new fields are nullable to support existing users
3. `google_id` field has unique constraint and index
4. Database migration runs without errors on local environment
5. Migration is reversible (rollback works)

**Technical Notes:**
- Migration file: `users/migrations/0005_add_google_oauth_fields.py`
- Use concurrent index creation for `google_id` field
- Default `auth_provider` to 'manual' for existing users
- Test migration with sample user data

**Definition of Done:**
- [ ] Migration created and tested locally
- [ ] Unique constraints and indexes added
- [ ] Migration runs successfully on empty and populated databases
- [ ] Rollback tested and works
- [ ] Documentation updated in `docs/architecture.md`

---

### Story 1.2: OAuth State Tracking Model
**As a** security engineer  
**I want** to track OAuth state tokens securely  
**So that** we can prevent CSRF attacks and replay attacks

**Acceptance Criteria:**
1. `GoogleOAuthState` model created with fields: `state_token`, `code_verifier`, `redirect_uri`, `nonce`, `created_at`, `used_at`, `ip_address`, `user_agent`, `expires_at`
2. State tokens are unique and indexed
3. Expiration is enforced (10-minute TTL)
4. Used state tokens cannot be reused
5. Model includes methods for validation and cleanup

**Technical Notes:**
- Model location: `auth/models.py`
- Add compound index on `(state_token, used_at)` for fast lookups
- Add index on `expires_at` for cleanup queries
- State tokens should be 128-character random strings
- PKCE `code_verifier` stored securely

**Definition of Done:**
- [ ] Model created with all required fields
- [ ] Indexes added for performance
- [ ] Migration runs successfully
- [ ] Model methods for validation implemented
- [ ] Unit tests written for state validation logic

---

### Story 1.3: OAuth State Cleanup Task
**As a** platform engineer  
**I want** expired OAuth states automatically cleaned up  
**So that** the database doesn't fill with stale data

**Acceptance Criteria:**
1. Celery Beat task runs every 15 minutes
2. Task deletes OAuth states older than 1 hour
3. Task logs number of states deleted
4. Task handles errors gracefully (doesn't crash worker)
5. Task can be triggered manually for testing

**Technical Notes:**
- Task file: `auth/tasks.py`
- Use `GoogleOAuthState.objects.filter(expires_at__lt=cutoff).delete()`
- Add monitoring for cleanup lag (alert if >10,000 expired states)
- Configure in `mysite/celery.py` beat schedule

**Definition of Done:**
- [ ] Celery task created and tested
- [ ] Beat schedule configured
- [ ] Task logs cleanup metrics
- [ ] Error handling implemented
- [ ] Manual trigger tested

---

### Story 1.4: Google OAuth Python Dependencies
**As a** backend developer  
**I want** Google OAuth libraries installed  
**So that** I can integrate with Google's OAuth API

**Acceptance Criteria:**
1. `google-auth==2.23.4+` added to `requirements.txt`
2. `google-auth-oauthlib==1.1.0+` added to `requirements.txt`
3. `google-auth-httplib2==0.1.1+` added to `requirements.txt`
4. All dependencies install without conflicts
5. Dependencies work in Docker container

**Technical Notes:**
- Version pinning to avoid breaking changes
- Test in both local venv and Docker environment
- Update `Dockerfile` if needed for system dependencies
- Document any system-level dependencies (libssl, etc.)

**Definition of Done:**
- [ ] Dependencies added to `requirements.txt`
- [ ] `pip install -r requirements.txt` succeeds
- [ ] Docker build succeeds
- [ ] Import statements work: `from google.oauth2 import id_token`

---

### Story 1.5: Google Cloud Console Setup & Configuration
**As a** DevOps engineer  
**I want** Google Cloud OAuth credentials configured  
**So that** developers can test OAuth flow locally

**Acceptance Criteria:**
1. Google Cloud project created (tinybeans-dev, tinybeans-prod)
2. OAuth 2.0 Client ID created for web application
3. Authorized redirect URIs configured (localhost + staging + prod)
4. Client ID and Secret stored securely in environment variables
5. Documentation created for setup process

**Technical Notes:**
- Development redirect URI: `http://localhost:3000/auth/google/callback`
- Staging: `https://staging.tinybeans.app/auth/google/callback`
- Production: `https://tinybeans.app/auth/google/callback`
- Use different OAuth clients for dev/staging/prod
- Enable Google+ API and Google OAuth2 API

**Environment Variables:**
```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

**Definition of Done:**
- [ ] Google Cloud project created
- [ ] OAuth credentials generated
- [ ] Environment variables documented in `.env.example`
- [ ] Test OAuth URL generation works
- [ ] Developer setup guide created

---

### Story 1.6: OAuth Configuration Settings
**As a** backend developer  
**I want** OAuth settings properly configured in Django  
**So that** the OAuth service can initialize correctly

**Acceptance Criteria:**
1. OAuth settings added to `settings.py`
2. Redirect URI whitelist configured
3. OAuth scopes defined
4. Rate limiting settings configured
5. Settings validated on startup

**Technical Notes:**
```python
# settings.py additions

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = env('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_OAUTH_CLIENT_SECRET = env('GOOGLE_OAUTH_CLIENT_SECRET')
GOOGLE_OAUTH_REDIRECT_URI = env('GOOGLE_OAUTH_REDIRECT_URI')

# Security: Allowed redirect URIs (whitelist)
OAUTH_ALLOWED_REDIRECT_URIS = [
    'https://tinybeans.app/auth/google/callback',
    'https://staging.tinybeans.app/auth/google/callback',
    'http://localhost:3000/auth/google/callback',
]

# OAuth state expiration (seconds)
OAUTH_STATE_EXPIRATION = 600  # 10 minutes

# Google OAuth scopes
GOOGLE_OAUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]
```

**Definition of Done:**
- [ ] All OAuth settings added to `settings.py`
- [ ] Settings use environment variables
- [ ] Whitelist includes all required URIs
- [ ] Settings validated on Django startup
- [ ] Missing env vars raise clear error messages

---

## Epic Acceptance Criteria

This epic is complete when:
- [ ] All 6 stories are completed and merged
- [ ] Database migrations are applied to dev environment
- [ ] OAuth state cleanup task is running
- [ ] Google Cloud Console is configured
- [ ] All dependencies are installed
- [ ] Settings are documented and validated
- [ ] Backend can be started without errors
- [ ] Integration tests pass for infrastructure components

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Migration locks table in production | Use concurrent index creation, test on copy of prod data |
| Google API credentials leaked | Store in environment variables, add to `.gitignore`, use secrets manager |
| Celery Beat not running | Add monitoring alert, document deployment checklist |
| Wrong redirect URI breaks OAuth | Whitelist validation, comprehensive testing |

---

## Testing Requirements

### Unit Tests
- User model field validation
- OAuth state validation logic
- State cleanup task functionality

### Integration Tests
- Database migration on populated database
- Celery Beat task execution
- Settings validation

### Manual Testing
- Verify migrations on local database
- Test cleanup task triggers manually
- Confirm Google Cloud Console access

---

## Documentation Updates

- [ ] Update `docs/architecture.md` with OAuth fields
- [ ] Create `docs/guides/google-cloud-setup.md`
- [ ] Update `.env.example` with OAuth variables
- [ ] Document Celery Beat schedule changes

---

## Dependencies & Blockers

**Upstream Dependencies:** None - this is the first epic

**Blocks:**
- Epic 2: OAuth API Implementation (cannot start without this infrastructure)
- Epic 3: Security Hardening (needs OAuth state model)

---

## Success Metrics

- Migration runs in < 5 seconds on dev database
- Cleanup task successfully deletes expired states
- Zero deployment failures due to missing configuration
- Developer setup time < 30 minutes

---

**Epic Owner**: Backend Team Lead  
**Stakeholders**: Backend Developers, DevOps, Security Team  
**Target Completion**: End of Sprint 1, Week 1

