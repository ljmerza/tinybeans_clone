# 🔐 Security Improvements - Quick Reference

## For Developers

### What Changed?

1. **TOTP Secrets are now encrypted** - No code changes needed, handled transparently
2. **Recovery codes are now hashed** - Service returns plain text, but stored as hashes
3. **Login has rate limiting** - 10/hour per IP, 5/hour per username
4. **Partial tokens are IP-bound** - Pass `request` to token functions
5. **Account lockout after failed 2FA** - Automatic, configurable in settings

---

## Quick Start

### 1. Update Your Code

#### Token Functions - Add `request` parameter:

**Before**:
```python
partial_token = generate_partial_token(user)
user = verify_partial_token(token)
```

**After**:
```python
partial_token = generate_partial_token(user, request)  # Add request
user = verify_partial_token(token, request)  # Add request
```

#### Recovery Codes - Work with plain text:

**Before**:
```python
codes = TwoFactorService.generate_recovery_codes(user)
for code in codes:
    print(code.code)  # Was a model object
```

**After**:
```python
codes = TwoFactorService.generate_recovery_codes(user)  # Returns list of strings
for code in codes:
    print(code)  # Already plain text string
```

---

### 2. Environment Setup

Add to `.env`:
```bash
# Generate this: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TWOFA_ENCRYPTION_KEY=your-key-here

# Optional - defaults shown
TWOFA_LOCKOUT_ENABLED=True
TWOFA_LOCKOUT_DURATION_MINUTES=30
TWOFA_LOCKOUT_THRESHOLD=5
```

---

### 3. Run Migration

```bash
python manage.py migrate auth_app
```

**⚠️ Warning**: Existing recovery codes will be invalidated!

---

## API Changes

### None! 🎉

All API endpoints maintain the same interface. Changes are internal only.

---

## Testing Your Changes

### Check if 2FA Setup Works:
```bash
curl -X POST http://localhost:8000/api/auth/2fa/setup/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"method": "totp"}'
```

### Check if Rate Limiting Works:
```bash
# Try to login 11 times rapidly
for i in {1..11}; do
  curl -X POST http://localhost:8000/api/auth/login/ \
    -d '{"username": "test", "password": "wrong"}' &
done
# Last request should get HTTP 429
```

### Check if Account Lockout Works:
```bash
# Fail 2FA 5 times
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/auth/2fa/verify/ \
    -d '{"code": "000000", "partial_token": "$TOKEN"}'
done
# 6th attempt should return lockout error
```

---

## Common Issues

### "Invalid or expired encryption key"
**Fix**: Set `TWOFA_ENCRYPTION_KEY` in your environment

### "Recovery codes not working"
**Fix**: Generate new codes after migration

### "Getting rate limited during development"
**Fix**: Temporarily remove `@ratelimit` decorators or use different IP/username

### "IP mismatch error"
**Fix**: Ensure your proxy/load balancer sets `X-Forwarded-For` header

---

## Performance Notes

- **Encryption**: Minimal overhead (~1ms per operation)
- **Hashing**: SHA-256 is fast (~0.1ms per code)
- **Rate Limiting**: Uses Redis cache, very fast
- **IP Binding**: No noticeable impact

---

## Security Best Practices

### DO:
✅ Keep encryption key in environment variables  
✅ Use HTTPS in production  
✅ Rotate encryption keys periodically  
✅ Monitor failed login attempts  
✅ Notify users of 2FA changes

### DON'T:
❌ Commit encryption key to source control  
❌ Disable rate limiting without good reason  
❌ Store recovery codes in plain text anywhere  
❌ Ignore account lockout notifications  
❌ Allow weak TOTP secrets

---

## Monitoring

### Key Metrics to Watch:
- Failed login attempts (should trigger alerts)
- Account lockouts (investigate patterns)
- Recovery code usage (might indicate compromised account)
- Rate limit hits (could be attack or misconfiguration)

### Log Entries to Monitor:
```python
# All recorded in TwoFactorAuditLog
- 2fa_login_failed
- 2fa_login_success
- recovery_code_used
- 2fa_enabled
- 2fa_disabled
```

---

## Rollback Plan

If you need to rollback:

1. **Revert code changes**:
```bash
git revert <commit-hash>
```

2. **Rollback migration**:
```bash
python manage.py migrate auth_app 0001_initial
```

3. **Remove dependencies** (optional):
```bash
pip uninstall cryptography django-ratelimit
```

**⚠️ Note**: TOTP secrets and recovery codes will be lost. Users must reconfigure 2FA.

---

## Need Help?

1. Check logs: `tail -f logs/django.log`
2. Check audit log: `TwoFactorAuditLog` model
3. Review full docs: `docs/SECURITY_IMPROVEMENTS_IMPLEMENTED.md`
4. Contact security team

---

**Last Updated**: October 1, 2024
