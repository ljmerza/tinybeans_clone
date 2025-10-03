# OAuth Security Incident Response Runbook

## Overview

This runbook provides step-by-step procedures for responding to OAuth-related security incidents.

**Last Updated**: 2025-01-12  
**Version**: 1.0  
**Owner**: Security Team

---

## Incident Classification

### Severity Levels

**P0 - Critical**: Active exploitation, data breach
**P1 - High**: Potential exploitation, security control bypass
**P2 - Medium**: Suspicious activity, failed attacks
**P3 - Low**: Anomalies, potential false positives

---

## Common OAuth Incidents

### Incident 1: Suspected Account Takeover

**Indicators**:
- Multiple failed OAuth attempts for same email
- OAuth link attempt on unverified account (should be blocked)
- Unusual login patterns (new location, device)

**Response Steps**:

1. **Immediate Actions** (5 minutes)
   ```bash
   # Check logs for the email
   grep "UNVERIFIED_ACCOUNT_EXISTS" /var/log/oauth.log | grep "victim@example.com"
   
   # Verify block was effective
   # Should see 403 responses, no account linking
   ```

2. **Investigate** (15 minutes)
   - Review OAuth security logs
   - Check if any linking occurred (should be NONE)
   - Identify attack source (IP addresses)
   - Check for related attempts

3. **Contain** (30 minutes)
   - If block failed: IMMEDIATELY disable OAuth
   - Lock affected accounts
   - Force password reset for impacted users
   - Block attacking IP addresses

4. **Notify** (1 hour)
   - Security team
   - Affected users
   - Compliance team (if required)

5. **Remediate** (varies)
   - Fix any bypasses discovered
   - Deploy patches
   - Re-enable OAuth after verification

6. **Document**
   - Incident timeline
   - Attack vector
   - Response actions
   - Lessons learned

---

### Incident 2: OAuth State Token Replay Attack

**Indicators**:
- Log entries: "State token already used"
- Multiple attempts with same state token
- High volume from single IP

**Response Steps**:

1. **Verify Protection** (5 minutes)
   ```bash
   # Check if replay was blocked
   grep "state_token_replay" /var/log/oauth.log
   
   # Should see rejections, no successful logins
   ```

2. **Investigate** (15 minutes)
   - Count replay attempts
   - Identify source IPs
   - Check if any succeeded (should be NONE)

3. **Action** (30 minutes)
   - If replay succeeded: INCIDENT ESCALATION to P0
   - If blocked successfully: Monitor and document
   - Rate limit attacking IPs
   - Alert security team

---

### Incident 3: Rate Limit Abuse

**Indicators**:
- High volume OAuth requests from single IP
- Distributed attack from multiple IPs
- Rate limit triggers spiking

**Response Steps**:

1. **Assess** (5 minutes)
   ```bash
   # Check rate limit triggers
   grep "oauth.rate_limit_exceeded" /var/log/oauth.log | wc -l
   
   # Identify attacking IPs
   grep "oauth.rate_limit_exceeded" /var/log/oauth.log | \
     grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" | sort | uniq -c | sort -rn
   ```

2. **Block** (15 minutes)
   - Add attacking IPs to firewall
   - Increase rate limits if needed (temporarily)
   - Enable CAPTCHA for repeated failures (future enhancement)

3. **Monitor** (ongoing)
   - Watch for distributed attacks
   - Check if attack shifts to new IPs
   - Alert if pattern continues

---

### Incident 4: Suspicious Google Account Linking

**Indicators**:
- Unusual linking patterns
- Links from unexpected locations
- Multiple accounts linked to same Google ID

**Response Steps**:

1. **Review** (10 minutes)
   ```bash
   # Check recent Google account links
   grep "oauth.account_linked" /var/log/oauth.log | tail -n 100
   
   # Look for anomalies
   ```

2. **Verify Legitimacy** (30 minutes)
   - Contact users if suspicious
   - Check if emails match
   - Review IP/location data

3. **Revoke If Needed** (immediate)
   - Unlink suspicious Google accounts
   - Force re-verification
   - Lock accounts if necessary

---

## Emergency Contacts

**Security Team**: security@tinybeans.app  
**On-Call Engineer**: [Phone Number]  
**Incident Commander**: [Name]  
**Google OAuth Support**: [If exists]

---

## Kill Switch Procedures

### Disable OAuth Immediately

```python
# In Django settings or via environment variable
GOOGLE_OAUTH_ENABLED = False
```

```bash
# Or via admin panel
python manage.py shell
>>> from django.conf import settings
>>> settings.GOOGLE_OAUTH_ENABLED = False
```

### Invalidate All OAuth States

```bash
python manage.py shell
>>> from auth.models import GoogleOAuthState
>>> GoogleOAuthState.objects.all().delete()
>>> print("All OAuth states invalidated")
```

### Force Logout All OAuth Users

```bash
# If using Redis for sessions
redis-cli FLUSHDB

# Or Django command
python manage.py clearsessions
```

---

## Post-Incident Actions

1. **Root Cause Analysis** (24 hours)
   - What happened?
   - How did it happen?
   - Why wasn't it prevented?

2. **Remediation** (varies)
   - Fix vulnerabilities
   - Update security controls
   - Deploy patches

3. **Prevention** (ongoing)
   - Update detection rules
   - Improve monitoring
   - Conduct training

4. **Documentation** (1 week)
   - Incident report
   - Timeline
   - Lessons learned
   - Process improvements

---

## Security Log Queries

### Find Failed OAuth Attempts
```bash
grep "oauth.callback.failure" /var/log/oauth.log | tail -n 50
```

### Find Security Blocks
```bash
grep "oauth.security_block" /var/log/oauth.log
```

### Find Account Takeover Attempts
```bash
grep "UNVERIFIED_ACCOUNT_EXISTS" /var/log/oauth.log
```

### Find Rate Limit Triggers
```bash
grep "oauth.rate_limit_exceeded" /var/log/oauth.log | \
  awk '{print $timestamp, $ip_address}' | sort | uniq -c
```

---

## Escalation Matrix

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| P0 | Immediate | Security Lead, CTO |
| P1 | < 1 hour | Security Team, Engineering Manager |
| P2 | < 4 hours | On-Call Engineer |
| P3 | < 24 hours | Team Review |

---

**Document Version**: 1.0  
**Next Review**: 2025-02-12  
**Last Tested**: Never (conduct drill)
