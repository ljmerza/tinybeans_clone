# OAuth Security Penetration Testing Checklist

## Overview

This document provides a comprehensive penetration testing checklist for the Google OAuth implementation. All tests should be performed before production deployment and after any OAuth-related code changes.

**Last Updated**: 2025-01-12  
**OAuth Implementation Version**: v1.0  
**Testing Framework**: Manual + OWASP ZAP

---

## Pre-Test Setup

### Test Environment
- [ ] Dedicated test environment configured
- [ ] Test Google OAuth credentials created
- [ ] Test user accounts created (verified, unverified, with/without Google)
- [ ] Rate limiting disabled for testing (re-enable after)
- [ ] Security logging enabled and monitored

### Testing Tools
- [ ] OWASP ZAP installed and configured
- [ ] Burp Suite (optional) for advanced testing
- [ ] curl or Postman for API testing
- [ ] Python scripts for automated attack scenarios

---

## Critical Test Scenarios

### ⚠️ Test 1: Account Takeover via Unverified Email (CRITICAL)

**Objective**: Verify linking to unverified accounts is blocked.

**Test Steps**:
1. Create account with victim@example.com, don't verify email
2. Attacker uses Google OAuth with victim@example.com
3. Attempt to complete OAuth callback

**Expected Results**:
- ✅ OAuth callback returns 403 Forbidden
- ✅ Error code: "UNVERIFIED_ACCOUNT_EXISTS"
- ✅ No account modification or linking occurs
- ✅ Security log entry: "oauth.security_block"

**Pass Criteria**: **MUST BLOCK** - This is the #1 account takeover vector

---

### Test 2: CSRF Attack via State Token Manipulation

**Objective**: Verify state token prevents cross-site request forgery.

**Test Steps**:
1. Start OAuth flow, capture state token
2. Attempt to use expired state token
3. Attempt to use state token twice (replay attack)
4. Attempt to use forged/random state token

**Expected Results**:
- ✅ Expired state: Rejected with "State token expired"
- ✅ Used state: Rejected with "State token already used"
- ✅ Forged state: Rejected with "State token not found"

**Pass Criteria**: All state token manipulations blocked

---

### Test 3: Open Redirect Attack

**Objective**: Verify redirect URI validation prevents open redirects.

**Test Steps**:
1. Attempt OAuth initiate with malicious redirect URIs
2. Try partial matches, path traversal, URL encoding bypasses

**Expected Results**:
- ✅ All malicious URIs rejected with 400 error
- ✅ Security log entry created for each attempt

**Pass Criteria**: No redirects to domains outside whitelist

---

### Test 4: PKCE Bypass

**Objective**: Verify PKCE code verifier is required and validated.

**Test Steps**:
1. Attempt callback without code_verifier
2. Attempt callback with wrong code_verifier

**Expected Results**:
- ✅ Callback rejects missing/wrong code_verifier
- ✅ Google validates PKCE (S256 method)

**Pass Criteria**: PKCE enforced end-to-end

---

### Test 5: Rate Limit Bypass

**Objective**: Verify rate limiting cannot be circumvented.

**Test Steps**:
1. Make rapid requests to OAuth endpoints
2. Try bypass techniques (headers, IPs, sessions)

**Expected Results**:
- ✅ Rate limit enforced after threshold
- ✅ 429 status code returned
- ✅ Bypass attempts logged

**Pass Criteria**: Rate limits cannot be bypassed

---

## Test Results Template

```markdown
# OAuth Security Test Results

**Date**: 2025-01-12
**Tester**: Security Team
**Environment**: Staging

## Summary
- Critical Tests Passed: 5/5 ✅
- All Security Controls: Verified

## Critical Test: Account Takeover Prevention
**Status**: ✅ PASSED
- Unverified account linking blocked
- 403 error returned correctly
- Security logging working

## Recommendations
- Deploy to production
- Enable security monitoring
- Schedule monthly re-tests

## Sign-off
Security Engineer: _______________
Date: _______________
```

---

**Document Version**: 1.0  
**Next Review**: 2025-02-12
