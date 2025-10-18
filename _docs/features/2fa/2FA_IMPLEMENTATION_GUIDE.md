# 2FA Implementation Quick Reference

## Overview
This document provides a quick reference for implementing 2FA with TOTP (Authenticator App), Email, and SMS methods based on ADR-003.

## Architecture Summary

```
Auth App (Core Logic)
├── 2FA Models (TwoFactorSettings, TwoFactorCode, RecoveryCode, TrustedDevice)
├── 2FA Service (TOTP, OTP generation, validation, recovery, device trust)
└── 2FA Handlers
    ├── TOTP Handler (pyotp, QR codes)
    ├── Email Handler → Emailing App (existing)
    └── SMS Handler → SMS App (new)
```

## Key Components

### 1. SMS App (New)
**Location**: `mysite/sms/`

**Purpose**: Encapsulate all SMS functionality
- Provider-agnostic SMS interface
- Twilio/AWS SNS implementations
- Celery tasks for async sending
- Reusable for future SMS needs (notifications, alerts, etc.)

### 2. Auth App (Enhanced)
**Location**: `mysite/auth/`

**Additions**:
- 5 new models for 2FA data (TwoFactorSettings, TwoFactorCode, RecoveryCode, TrustedDevice, TwoFactorAuditLog)
- TwoFactorService for business logic (TOTP + OTP)
- TrustedDeviceService for Remember Me feature
- 12 new API endpoints (including device management)
- Modified login flow with device trust check
- QR code generation
- Recovery code export (TXT/PDF)
- Device fingerprinting

### 3. Emailing App (Enhanced)
**Location**: `mysite/emailing/`

**Additions**:
- TwoFactorMailer class
- 3 new email templates
- New Celery tasks

## Implementation Checklist

### Phase 1: SMS App Foundation
- [ ] Create `mysite/sms/` app structure
- [ ] Implement `BaseSMSProvider` abstract class
- [ ] Implement `TwilioProvider`
- [ ] Create `SMSService`
- [ ] Add Celery task `send_sms_async`
- [ ] Write unit tests
- [ ] Add to `INSTALLED_APPS`
- [ ] Install dependencies: `pip install twilio`

### Phase 2: TOTP Implementation
- [ ] Install dependencies: `pip install pyotp qrcode Pillow`
- [ ] Add `totp_secret` field to TwoFactorSettings model
- [ ] Implement TOTP secret generation
- [ ] Implement QR code generation
- [ ] Add TOTP verification method
- [ ] Create TOTP setup endpoint
- [ ] Test with Google Authenticator/Authy
- [ ] Write unit tests for TOTP

### Phase 3: Auth Models & Core Logic
- [ ] Add 2FA models to `auth/models.py`
- [ ] Create migrations
- [ ] Implement `TwoFactorService` with TOTP methods
- [ ] Add OTP generation logic (email/SMS)
- [ ] Add rate limiting logic
- [ ] Add recovery code logic
- [ ] Write service tests

### Phase 4: Recovery Code Export
- [ ] Install dependency: `pip install reportlab`
- [ ] Implement TXT export function
- [ ] Implement PDF export function
- [ ] Create download endpoint
- [ ] Add download button to UI
- [ ] Test both formats
- [ ] Write tests for export

### Phase 5: Email/SMS 2FA
- [ ] Create email templates
- [ ] Add `TwoFactorMailer` to `emails/mailers.py`
- [ ] Add email tasks to `emails/tasks.py`
- [ ] Update auth views for 2FA flow
- [ ] Add 2FA endpoints
- [ ] Connect SMS app to auth
- [ ] Add phone number validation
- [ ] Test delivery methods
- [ ] Write integration tests

### Phase 6: Security & Polish
- [ ] Implement rate limiting
- [ ] Add audit logging
- [ ] Complete frontend flows
- [ ] Add security tests
- [ ] Penetration testing
- [ ] Documentation

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/2fa/setup/` | Start 2FA setup (returns QR for TOTP) |
| POST | `/auth/2fa/verify-setup/` | Complete 2FA setup |
| POST | `/auth/2fa/disable/` | Disable 2FA |
| GET | `/auth/2fa/status/` | Get 2FA settings |
| POST | `/auth/2fa/send-code/` | Resend OTP (email/SMS only) |
| POST | `/auth/2fa/verify/` | Verify code on login (accepts remember_me) |
| POST | `/auth/2fa/recovery-codes/generate/` | Generate recovery codes |
| GET | `/auth/2fa/recovery-codes/download/` | Download codes (TXT/PDF) |
| POST | `/auth/2fa/recovery-codes/verify/` | Use recovery code |
| GET | `/auth/2fa/trusted-devices/` | List trusted devices |
| DELETE | `/auth/2fa/trusted-devices/{id}/` | Remove trusted device |
| POST | `/auth/2fa/trusted-devices/remove/` | Remove device by ID |

## Database Schema

### TwoFactorSettings
- user (FK to User)
- is_enabled (bool)
- preferred_method (totp/email/sms)
- totp_secret (base32 string, for TOTP)
- phone_number (optional, for SMS)
- backup_email (optional)

### TwoFactorCode
- user (FK to User)
- code (6 digits)
- method (email/sms, not used for TOTP)
- purpose (login/setup/disable)
- is_used (bool)
- attempts (int)
- expires_at (datetime)

### RecoveryCode
- user (FK to User)
- code (16 chars, format: XXXX-XXXX-XXXX)
- is_used (bool)
- used_at (datetime)

### TrustedDevice (NEW - Remember Me)
- user (FK to User)
- device_id (unique identifier, 64 chars)
- device_name (browser/OS info)
- ip_address (IP)
- user_agent (string)
- last_used_at (datetime)
- expires_at (datetime)
- created_at (datetime)

### TwoFactorAuditLog
- user (FK to User)
- action (string)
- method (email/sms/totp/device_trust)
- ip_address (IP)
- device_id (optional)
- success (bool)
- created_at (datetime)

## Configuration Settings

```python
# Required environment variables
TWOFA_ENABLED=True
TWOFA_ISSUER_NAME=Tinybeans  # For TOTP QR codes
SMS_PROVIDER=twilio  # or 'aws_sns'
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890

# Optional (have defaults)
TWOFA_CODE_EXPIRY_MINUTES=10
TWOFA_MAX_ATTEMPTS=5
TWOFA_RATE_LIMIT_WINDOW=900
TWOFA_RATE_LIMIT_MAX=3

# Trusted Devices (Remember Me)
TWOFA_TRUSTED_DEVICE_ENABLED=True
TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS=30
TWOFA_TRUSTED_DEVICE_MAX_COUNT=5
```

## Python Dependencies

```bash
# Core 2FA
pip install pyotp==2.9.0              # TOTP (RFC 6238)
pip install qrcode==7.4.2             # QR code generation
pip install Pillow==10.1.0            # Image processing
pip install reportlab==4.0.7          # PDF generation

# SMS (optional - choose one)
pip install twilio==8.10.0            # For Twilio
pip install boto3==1.29.7             # For AWS SNS
```

## User Flows

### Setup Flow (TOTP)
1. User enables 2FA in settings
2. Selects "Authenticator App" method
3. Scans QR code with Google Authenticator/Authy
4. Enters 6-digit code to verify
5. Downloads recovery codes (TXT or PDF)
6. 2FA is enabled ✓

### Setup Flow (Email/SMS)
1. User enables 2FA in settings
2. Selects method (email/SMS)
3. Enters phone number (if SMS)
4. Receives OTP
5. Enters OTP to verify
6. Downloads recovery codes
7. 2FA is enabled ✓
8. 2FA enabled ✓

### Login Flow (2FA enabled)
1. User enters username/password
2. System validates credentials
3. System sends OTP
4. User enters OTP
5. System validates OTP
6. User logged in ✓

### Recovery Flow
1. User enters username/password
2. User clicks "Use recovery code"
3. User enters recovery code
4. System validates code
5. Code marked as used
6. User logged in ✓
7. Alert email sent

## Testing Strategy

### Unit Tests
- OTP generation (randomness, length)
- OTP validation (correct, incorrect, expired)
- Recovery code generation
- Rate limiting logic
- SMS provider implementations

### Integration Tests
- Complete setup flow
- Complete login flow
- Recovery code flow
- Email delivery
- SMS delivery
- Rate limit enforcement

### E2E Tests
- Full user journey: signup → setup → login
- Recovery scenarios
- Multiple devices
- Browser compatibility

## Security Checklist

- [ ] OTP codes are cryptographically random
- [ ] OTPs expire after 10 minutes
- [ ] Rate limiting prevents brute force
- [ ] Recovery codes are single-use
- [ ] All 2FA events are logged
- [ ] Partial tokens have limited scope
- [ ] HTTPS enforced on all endpoints
- [ ] Phone numbers validated
- [ ] User notifications on changes
- [ ] Account lockout after max failures

## Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1 | 1 week | SMS app, providers |
| Phase 2 | 1 week | Models, services |
| Phase 3 | 1 week | Email 2FA complete |
| Phase 4 | 1 week | SMS 2FA complete |
| Phase 5 | 1 week | Security, polish |
| **Total** | **5 weeks** | Full 2FA system |

## Future Enhancements

1. **TOTP Support** (Google Authenticator)
   - No delivery costs
   - Works offline
   - Industry standard

2. **WebAuthn/FIDO2** (Hardware keys)
   - Phishing-resistant
   - Highest security
   - For enterprise tier

3. **Backup Methods**
   - Multiple methods per user
   - Automatic fallback

4. **SMS Fallback Providers**
   - Multiple SMS providers
   - Automatic failover

5. **Push Notifications**
   - Mobile app approval
   - No OTP typing needed

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| SMS not delivered | Check Twilio logs, verify phone format |
| Email in spam | Update SPF/DKIM records |
| OTP expired | Resend with longer expiry |
| User locked out | Support can disable 2FA after identity verification |
| Rate limit too strict | Adjust settings in Django admin |
| Celery task fails | Check logs, implement retry logic |

## References

- ADR-003: Full architecture decision record
- [OWASP 2FA Guidelines](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)
- [Twilio Python SDK](https://www.twilio.com/docs/libraries/python)
- [Django REST Framework](https://www.django-rest-framework.org/)
