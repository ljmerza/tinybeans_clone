# Epic 5: OAuth Testing, Documentation & Deployment

**Epic ID**: OAUTH-005  
**Status**: Blocked (depends on all previous epics)  
**Priority**: P0 - Launch Blocker  
**Sprint**: Sprint 2, Week 2  
**Estimated Effort**: 5 story points  
**Dependencies**: OAUTH-001, OAUTH-002, OAUTH-003, OAUTH-004  
**Related ADR**: [ADR-010: Google OAuth Integration](../architecture/adr/ADR-010-GOOGLE-OAUTH-INTEGRATION.md)

---

## Epic Goal

Ensure OAuth implementation is production-ready through comprehensive testing, complete documentation, staging deployment, and launch preparation. This epic gates the OAuth feature for production release.

---

## Business Value

- Validates OAuth works correctly before customer exposure
- Reduces production incidents through thorough testing
- Enables smooth user adoption through documentation
- Ensures team can support and maintain OAuth long-term

---

## User Stories

### Story 5.1: Integration Test Suite
**As a** QA engineer  
**I want** comprehensive integration tests  
**So that** OAuth works correctly end-to-end

**Acceptance Criteria:**
1. Tests cover all 5 account scenarios (new user, existing verified, etc.)
2. Tests verify complete OAuth flow (initiate → Google → callback → JWT)
3. Tests validate security measures (rate limiting, PKCE, state validation)
4. Tests run in CI/CD pipeline
5. Tests use mocked Google API responses
6. All tests pass before merge

**Test Scenarios:**
1. **New User Signup**
   - User has no account
   - Clicks "Sign up with Google"
   - Creates new account via OAuth
   - Email auto-verified
   - JWT tokens issued

2. **Existing Verified User Login**
   - User has verified manual account
   - Clicks "Sign in with Google"
   - Google ID linked to account
   - Auth provider becomes 'hybrid'
   - JWT tokens issued

3. **Blocked Unverified Account**
   - User has unverified manual account
   - Clicks "Sign in with Google"
   - Returns 403 error
   - Error message shown
   - User not logged in

4. **Hybrid Account Login**
   - User already has Google linked
   - Clicks "Sign in with Google"
   - Logs in successfully
   - JWT tokens issued

5. **Account Linking from Settings**
   - Authenticated user
   - Goes to settings
   - Clicks "Link Google Account"
   - OAuth flow completes
   - Google ID linked

**Technical Notes:**
```python
# tests/integration/test_oauth_flow.py
import pytest
from unittest.mock import patch, MagicMock

class TestOAuthFlow:
    @patch('auth.services.google_oauth_service.requests.post')
    def test_new_user_signup_via_google(self, mock_post):
        # Mock Google API responses
        mock_post.return_value.json.return_value = {
            'access_token': 'mock_access_token',
            'id_token': 'mock_id_token',
        }
        
        # Step 1: Initiate OAuth
        response = self.client.post('/api/auth/google/initiate/', {
            'redirect_uri': 'http://localhost:3000/auth/google/callback'
        })
        assert response.status_code == 200
        state = response.data['state']
        
        # Step 2: Callback (mock Google redirect)
        response = self.client.post('/api/auth/google/callback/', {
            'code': 'mock_authorization_code',
            'state': state,
        })
        assert response.status_code == 200
        assert response.data['account_action'] == 'created'
        assert response.data['user']['email_verified'] == True
        assert 'access' in response.data['tokens']
```

**Definition of Done:**
- [ ] All 5 scenarios have tests
- [ ] Tests run in CI/CD
- [ ] Code coverage >90% for OAuth code
- [ ] Tests use mocked Google API
- [ ] Tests are maintainable and documented

---

### Story 5.2: Load and Performance Testing
**As a** platform engineer  
**I want** OAuth endpoints load tested  
**So that** they handle production traffic

**Acceptance Criteria:**
1. Load test simulates 1000 concurrent users
2. OAuth initiate endpoint handles 100 req/sec
3. OAuth callback endpoint handles 50 req/sec
4. p95 latency < 500ms for all endpoints
5. No errors under normal load
6. Rate limiting effective under attack simulation

**Load Test Scenarios:**
- **Normal Load**: 100 users signing up via Google over 10 minutes
- **Peak Load**: 500 concurrent OAuth flows
- **Attack Simulation**: 10,000 requests in 1 minute (rate limiting test)
- **Sustained Load**: 24-hour test with constant traffic

**Tools:**
- k6 for load testing
- Grafana for monitoring
- Prometheus for metrics

**Technical Notes:**
```javascript
// k6 load test script
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 }, // Ramp up
    { duration: '5m', target: 100 }, // Stay at 100
    { duration: '2m', target: 500 }, // Peak
    { duration: '5m', target: 500 }, // Sustained peak
    { duration: '2m', target: 0 },   // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'], // 95% under 500ms
    'http_req_failed': ['rate<0.01'],   // <1% errors
  },
};

export default function () {
  // Initiate OAuth
  let initiateRes = http.post(
    'https://api.tinybeans.app/api/auth/google/initiate/',
    JSON.stringify({
      redirect_uri: 'https://tinybeans.app/auth/google/callback'
    })
  );
  
  check(initiateRes, {
    'status is 200': (r) => r.status === 200,
    'has oauth url': (r) => r.json('google_oauth_url') !== undefined,
  });
  
  sleep(1);
}
```

**Definition of Done:**
- [ ] Load tests written and documented
- [ ] Tests run against staging environment
- [ ] Performance meets criteria
- [ ] Bottlenecks identified and fixed
- [ ] Load test report created

---

### Story 5.3: User Documentation
**As a** user  
**I want** clear documentation about Google sign-in  
**So that** I understand how to use it

**Documentation Required:**
1. **Help Article**: "How to sign in with Google"
2. **Help Article**: "How to link your Google account"
3. **Help Article**: "How to unlink your Google account"
4. **FAQ**: Common OAuth questions
5. **Troubleshooting Guide**: What to do if OAuth fails

**Content Outline:**

**"How to sign in with Google"**
- What is Google sign-in?
- Benefits of using Google
- Step-by-step instructions with screenshots
- What happens to my data?
- Can I still use my password?

**"Troubleshooting Google Sign-In"**
- "Unverified account exists" error
- "Session expired" error
- "Too many attempts" error
- Google doesn't redirect back
- Can't link Google account

**Definition of Done:**
- [ ] All help articles written
- [ ] Screenshots captured
- [ ] Content reviewed by product team
- [ ] Published to help center
- [ ] Linked from OAuth error messages

---

### Story 5.4: Developer Documentation
**As a** developer  
**I want** technical OAuth documentation  
**So that** I can maintain and extend OAuth

**Documentation Required:**
1. **Architecture Documentation**: Update `docs/architecture.md`
2. **API Documentation**: OpenAPI spec for OAuth endpoints
3. **Developer Guide**: How to test OAuth locally
4. **Runbook**: OAuth incident response procedures
5. **Security Guide**: OAuth security considerations

**API Documentation Example:**
```yaml
# OpenAPI spec for OAuth endpoints
/api/auth/google/initiate/:
  post:
    summary: Initiate Google OAuth flow
    tags: [Authentication]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              redirect_uri:
                type: string
                format: uri
                example: https://tinybeans.app/auth/google/callback
    responses:
      200:
        description: OAuth URL generated
        content:
          application/json:
            schema:
              type: object
              properties:
                google_oauth_url:
                  type: string
                  format: uri
                state:
                  type: string
                expires_in:
                  type: integer
      400:
        description: Invalid redirect URI
```

**Developer Guide Topics:**
- Setting up Google Cloud Console
- Configuring local environment
- Testing OAuth flow locally
- Debugging OAuth issues
- Monitoring OAuth metrics

**Runbook Topics:**
- OAuth incident classification
- Common failure modes
- Debugging procedures
- Rollback procedures
- Escalation contacts

**Definition of Done:**
- [ ] All documentation written
- [ ] Code examples tested
- [ ] Reviewed by team
- [ ] Published to docs site
- [ ] Added to onboarding materials

---

### Story 5.5: Staging Deployment & Validation
**As a** DevOps engineer  
**I want** OAuth deployed to staging  
**So that** it can be validated before production

**Acceptance Criteria:**
1. OAuth deployed to staging environment
2. Google Cloud Console configured for staging
3. Environment variables configured
4. Database migrations applied
5. Celery Beat running (OAuth cleanup)
6. Manual QA testing completed
7. Stakeholder sign-off obtained

**Staging Validation Checklist:**
- [ ] OAuth initiate endpoint returns valid Google URL
- [ ] Can complete OAuth flow in browser
- [ ] New user account created correctly
- [ ] Existing user account linked correctly
- [ ] Unverified account blocked correctly
- [ ] Rate limiting works
- [ ] Error messages display correctly
- [ ] Monitoring dashboards show data
- [ ] Logs are being captured
- [ ] Alerts are configured

**Technical Notes:**
- Staging URL: `https://staging.tinybeans.app`
- Google OAuth Client: tinybeans-staging
- Test accounts: Create test Google account for QA
- Database: staging-db (separate from production)

**Definition of Done:**
- [ ] Deployed to staging
- [ ] All validation checks pass
- [ ] Manual QA completed
- [ ] Product team sign-off
- [ ] Security team sign-off
- [ ] Ready for production deployment

---

### Story 5.6: Production Launch Preparation
**As a** product manager  
**I want** a launch plan for OAuth  
**So that** rollout is smooth and successful

**Launch Plan Components:**
1. **Feature Flag Strategy**
   - Start with 10% of users
   - Increase to 50% after 24 hours
   - 100% after 1 week if no issues

2. **Communication Plan**
   - Email to existing users announcing feature
   - In-app banner promoting Google sign-in
   - Social media announcement
   - Blog post about OAuth benefits

3. **Monitoring Dashboard**
   - OAuth success/failure rates
   - Account creation breakdown
   - Google API latency
   - Error rates by type

4. **Success Metrics**
   - Target: 30% of new signups use Google
   - Target: 15% improvement in signup conversion
   - Target: <5% OAuth error rate
   - Target: Zero security incidents

5. **Rollback Plan**
   - Disable feature flag
   - Revert migrations if needed
   - Communication to affected users

**Launch Checklist:**
- [ ] Production environment configured
- [ ] Google OAuth client created (production)
- [ ] Feature flag configured (off by default)
- [ ] Monitoring dashboard created
- [ ] Alerts configured
- [ ] Rollback procedure documented
- [ ] On-call engineer assigned
- [ ] Communication materials prepared
- [ ] Launch date/time scheduled
- [ ] Stakeholders notified

**Go/No-Go Criteria:**
- All epics completed (OAUTH-001 through OAUTH-005)
- All tests passing
- Security sign-off obtained
- Staging validation complete
- Monitoring in place
- Team trained on OAuth support

**Definition of Done:**
- [ ] Launch plan created and approved
- [ ] Go/no-go checklist complete
- [ ] Team briefed on launch
- [ ] Ready for production deployment

---

## Epic Acceptance Criteria

This epic is complete when:
- [ ] All 6 stories completed
- [ ] Integration tests passing (>90% coverage)
- [ ] Load tests show acceptable performance
- [ ] User documentation published
- [ ] Developer documentation complete
- [ ] Staging deployment validated
- [ ] Production launch plan approved
- [ ] Go/no-go criteria met

---

## Testing Summary

### Test Coverage Goals
- Unit Tests: >90% coverage
- Integration Tests: All scenarios covered
- E2E Tests: Critical paths automated
- Load Tests: Performance validated
- Security Tests: Penetration testing complete

### Test Types Completed
- [ ] Unit tests (backend)
- [ ] Unit tests (frontend)
- [ ] Integration tests
- [ ] E2E tests
- [ ] Load/performance tests
- [ ] Security/penetration tests
- [ ] Accessibility tests
- [ ] Visual regression tests

---

## Documentation Summary

### Documentation Deliverables
- [ ] User help articles
- [ ] Developer guide
- [ ] API documentation
- [ ] Architecture updates
- [ ] Security runbook
- [ ] Operations runbook
- [ ] Launch communications

---

## Launch Readiness Criteria

**Technical Readiness:**
- [ ] All tests passing
- [ ] Performance meets targets
- [ ] Security validated
- [ ] Monitoring configured

**Operational Readiness:**
- [ ] Team trained
- [ ] Documentation complete
- [ ] Runbooks created
- [ ] On-call coverage assigned

**Business Readiness:**
- [ ] Stakeholder sign-off
- [ ] Communications ready
- [ ] Success metrics defined
- [ ] Rollback plan documented

---

## Success Metrics

### Launch Week Metrics
- OAuth adoption rate: >20% of new signups
- OAuth success rate: >95%
- User-reported issues: <10
- System uptime: >99.9%

### Month 1 Metrics
- OAuth adoption: >30% of new signups
- Signup conversion improvement: >15%
- Support tickets: <5/week
- Zero security incidents

---

**Epic Owner**: Engineering Manager  
**Stakeholders**: Full Team + Product + Security  
**Target Completion**: End of Sprint 2, Week 2  
**Launch Date**: TBD (after Go/No-Go)

