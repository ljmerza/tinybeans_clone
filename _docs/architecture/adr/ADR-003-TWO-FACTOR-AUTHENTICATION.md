# ADR-003: Two-Factor Authentication (2FA) Architecture

## Status
Proposed

## Context

The Tinybeans application needs to implement Two-Factor Authentication (2FA) to enhance security for user accounts. This additional layer of security is critical for protecting sensitive family data, photos, and personal information.

### Requirements

1. Support multiple 2FA methods to accommodate different user preferences
2. Provide a fallback mechanism if primary 2FA method is unavailable
3. Maintain existing authentication flow with minimal disruption
4. Allow users to enable/disable 2FA per account
5. Support recovery codes for account recovery
6. Time-based OTP codes with reasonable expiration windows
7. Rate limiting to prevent brute force attacks
8. User-friendly setup and verification process

### Current Architecture

- **Auth App**: Handles login, signup, token refresh, and password management
- **Emailing App**: Already exists with Celery tasks for async email sending
- **Users App**: Manages user profiles and settings

## Decision

We will implement a multi-method 2FA system with the following architecture:

### 2FA Methods Supported

1. **Authenticator App (TOTP)** (Primary recommended method)
   - Time-based One-Time Passwords (RFC 6238)
   - Works offline (no delivery required)
   - Industry standard (Google Authenticator, Authy, 1Password, etc.)
   - No per-use costs
   - Most secure option

2. **Email OTP** (Secondary method)
   - Leverages existing email infrastructure
   - No additional third-party costs
   - Widely accessible (all users have email)
   - Good fallback option

3. **SMS OTP** (Tertiary method)
   - Requires new SMS app for encapsulation
   - Uses third-party SMS service (Twilio/AWS SNS)
   - Additional per-message costs
   - Quick delivery to mobile devices

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Web Frontend                          │
│  Login → 2FA Challenge → Verify OTP → Success               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                         Auth App                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  2FA Core Logic                                       │  │
│  │  - OTP Generation & Validation                        │  │
│  │  - Rate Limiting                                      │  │
│  │  - Recovery Codes                                     │  │
│  │  - 2FA State Management                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Email 2FA        │  │ SMS 2FA          │                │
│  │ Handler          │  │ Handler          │                │
│  └──────────────────┘  └──────────────────┘                │
└──────────┬────────────────────────┬─────────────────────────┘
           ↓                        ↓
┌──────────────────────┐  ┌──────────────────────┐
│   Emailing App       │  │   SMS App (New)      │
│   - Email tasks      │  │   - SMS tasks        │
│   - Templates        │  │   - Provider API     │
│   - Celery queue     │  │   - Celery queue     │
└──────────────────────┘  └──────────────────────┘
```

### Component Breakdown

#### 1. Auth App (Core 2FA Logic)

**New Models:**
```python
# mysite/auth/models.py

class TwoFactorSettings(models.Model):
    """User's 2FA preferences and configuration"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='twofa_settings')
    is_enabled = models.BooleanField(default=False)
    preferred_method = models.CharField(
        max_length=20,
        choices=[('totp', 'Authenticator App'), ('email', 'Email'), ('sms', 'SMS')],
        default='totp'
    )
    totp_secret = models.CharField(max_length=32, blank=True, null=True)  # Base32 encoded secret
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    backup_email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TwoFactorCode(models.Model):
    """Temporary OTP codes for verification"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)  # 6-digit OTP
    method = models.CharField(max_length=20)  # 'email' or 'sms'
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('login', 'Login Verification'),
            ('setup', 'Setup Verification'),
            ('disable', 'Disable 2FA')
        ]
    )
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'code', 'is_used']),
            models.Index(fields=['expires_at']),
        ]

class RecoveryCode(models.Model):
    """Recovery codes for account access when 2FA is unavailable"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recovery_codes')
    code = models.CharField(max_length=16, unique=True)  # e.g., "XXXX-XXXX-XXXX"
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class TrustedDevice(models.Model):
    """Trusted devices for 2FA skip (Remember Me feature)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trusted_devices')
    device_id = models.CharField(max_length=64, unique=True)  # Unique device identifier
    device_name = models.CharField(max_length=255)  # Browser/OS info
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    last_used_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()  # When trust expires
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'device_id']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = [['user', 'device_id']]

class TwoFactorAuditLog(models.Model):
    """Audit log for 2FA events"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # 'enabled', 'disabled', 'verified', 'failed', 'trusted_device_added'
    method = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    device_id = models.CharField(max_length=64, blank=True)  # For tracking device-specific events
    success = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
```

**New Services:**
```python
# mysite/auth/services/twofa_service.py

class TwoFactorService:
    """Core 2FA business logic"""
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP code for email/SMS"""
    
    @staticmethod
    def generate_totp_secret() -> str:
        """Generate TOTP secret key (base32 encoded)"""
    
    @staticmethod
    def generate_totp_qr_code(user, secret) -> str:
        """Generate QR code URI for authenticator apps"""
        # Returns otpauth:// URI
    
    @staticmethod
    def verify_totp(user, code) -> bool:
        """Verify TOTP code from authenticator app"""
        
    @staticmethod
    def send_otp(user, method='email', purpose='login') -> TwoFactorCode:
        """Generate and send OTP via email/SMS"""
        
    @staticmethod
    def verify_otp(user, code, purpose='login') -> bool:
        """Verify OTP code and mark as used"""
        
    @staticmethod
    def generate_recovery_codes(user, count=10) -> List[str]:
        """Generate recovery codes for user"""
        
    @staticmethod
    def verify_recovery_code(user, code) -> bool:
        """Verify and consume recovery code"""
        
    @staticmethod
    def export_recovery_codes(user, format='txt') -> str:
        """Export recovery codes in downloadable format (txt/pdf)"""
        
    @staticmethod
    def is_rate_limited(user) -> bool:
        """Check if user has exceeded attempt limits"""
    
    @staticmethod
    def generate_device_id(request) -> str:
        """Generate unique device identifier from request"""
        
    @staticmethod
    def add_trusted_device(user, request, days=30) -> TrustedDevice:
        """Add current device to trusted devices list"""
        
    @staticmethod
    def is_trusted_device(user, device_id) -> bool:
        """Check if device is trusted and not expired"""
        
    @staticmethod
    def remove_trusted_device(user, device_id) -> bool:
        """Remove device from trusted list"""
        
    @staticmethod
    def get_trusted_devices(user) -> List[TrustedDevice]:
        """Get all active trusted devices for user"""
        
    @staticmethod
    def cleanup_expired_devices():
        """Clean up expired trusted devices (scheduled task)"""
```

**New API Endpoints:**
```python
# mysite/auth/urls.py (additions)

POST /auth/2fa/setup/          # Initiate 2FA setup (returns QR code for TOTP)
POST /auth/2fa/verify-setup/   # Verify code and complete setup
POST /auth/2fa/disable/        # Disable 2FA (requires verification)
GET  /auth/2fa/status/         # Get current 2FA settings
POST /auth/2fa/send-code/      # Resend OTP code (email/SMS only)
POST /auth/2fa/verify/         # Verify code during login (accepts remember_me param)
POST /auth/2fa/recovery-codes/generate/   # Generate new recovery codes
GET  /auth/2fa/recovery-codes/download/   # Download recovery codes (txt/pdf)
POST /auth/2fa/recovery-codes/verify/     # Use recovery code

# Trusted Devices (Remember Me)
GET  /auth/2fa/trusted-devices/         # List all trusted devices
POST /auth/2fa/trusted-devices/remove/  # Remove a trusted device
DELETE /auth/2fa/trusted-devices/{device_id}/  # Delete specific device
```
POST /auth/2fa/recovery-codes/verify/     # Use recovery code
```

**Modified Login Flow:**
```python
# mysite/auth/views.py (enhanced)

class LoginView(APIView):
    """
    1. Validate username/password
    2. If 2FA enabled → send OTP, return partial token
    3. If 2FA disabled → return full tokens
    """

class TwoFactorVerifyView(APIView):
    """
    1. Validate partial token + OTP code
    2. Mark code as used
    3. Return full access/refresh tokens
    4. Log successful verification
    """
```

#### 2. SMS App (New Django App)

**Purpose:** Encapsulate all SMS sending logic and provider integration

**Structure:**
```
mysite/sms/
├── __init__.py
├── apps.py
├── providers/
│   ├── __init__.py
│   ├── base.py          # Abstract base provider
│   ├── twilio.py        # Twilio implementation
│   └── aws_sns.py       # AWS SNS implementation
├── tasks.py             # Celery tasks
├── services.py          # SMS service
└── tests/
    ├── test_providers.py
    └── test_tasks.py
```

**Implementation:**
```python
# mysite/sms/providers/base.py

class BaseSMSProvider(ABC):
    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS to phone number"""

# mysite/sms/providers/twilio.py

class TwilioProvider(BaseSMSProvider):
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS via Twilio"""

# mysite/sms/services.py

class SMSService:
    @staticmethod
    def get_provider() -> BaseSMSProvider:
        """Get configured SMS provider"""
        
    @staticmethod
    def send_2fa_code(phone_number: str, code: str) -> bool:
        """Send 2FA code via SMS"""

# mysite/sms/tasks.py

@shared_task
def send_sms_async(phone_number: str, message: str):
    """Async task to send SMS"""
    provider = SMSService.get_provider()
    return provider.send_sms(phone_number, message)
```

#### 3. Emailing App (Enhanced)

**New additions:**
```python
# mysite/emails/mailers.py (additions)

class TwoFactorMailer:
    @staticmethod
    def send_2fa_code(user, code):
        """Send 2FA verification code via email"""
        
    @staticmethod
    def send_2fa_enabled_notification(user):
        """Notify user that 2FA was enabled"""
        
    @staticmethod
    def send_2fa_disabled_notification(user):
        """Notify user that 2FA was disabled"""

# mysite/emails/tasks.py (additions)

@shared_task
def send_2fa_code_email(user_id, code):
    """Async task to send 2FA code email"""
```

**New templates:**
```
mysite/emails/templates/emails/
├── 2fa_code.html
├── 2fa_code.txt
├── 2fa_enabled.html
├── 2fa_enabled.txt
├── 2fa_disabled.html
└── 2fa_disabled.txt
```

### Authentication Flow

#### Setup Flow (TOTP - Authenticator App)
```
1. User navigates to security settings
2. User selects "Authenticator App" method
3. System generates TOTP secret
4. System generates QR code with otpauth:// URI
5. User scans QR code with authenticator app (Google Authenticator, Authy, etc.)
6. User enters 6-digit code from app to verify setup
7. System validates TOTP code
8. System generates recovery codes
9. User downloads/saves recovery codes (txt or PDF)
10. 2FA is enabled
```

#### Setup Flow (Email/SMS)
```
1. User navigates to security settings
2. User selects 2FA method (email/SMS)
3. If SMS: User enters phone number
4. System generates OTP and sends via selected method
5. User enters OTP to verify
6. System generates recovery codes
7. User downloads/saves recovery codes
8. 2FA is enabled
```

#### Login Flow (with TOTP enabled)
```
1. User submits username/password
2. System validates credentials
3. System checks if device is trusted (via device_id cookie/header)
4a. If trusted device: Skip 2FA, return full tokens
4b. If not trusted: Prompt for TOTP code
5. System returns partial token (limited scope)
6. User opens authenticator app
7. User enters current 6-digit TOTP code
8. User optionally checks "Remember this device for 30 days"
9. System verifies TOTP code
10. If remember_me: System generates device_id and creates TrustedDevice
11. System returns full access + refresh tokens (+ device_id if remember_me)
12. User is logged in
```

#### Login Flow (with Email/SMS enabled)
```
1. User submits username/password
2. System validates credentials
3. System checks if device is trusted
4a. If trusted device: Skip 2FA, return full tokens
4b. If not trusted: Generate and send OTP
5. System sends OTP via user's preferred method
6. System returns partial token (limited scope)
7. User enters OTP
8. User optionally checks "Remember this device for 30 days"
9. System verifies OTP
10. If remember_me: System creates TrustedDevice entry
11. System returns full access + refresh tokens (+ device_id if remember_me)
12. User is logged in
```

#### Recovery Flow
```
1. User submits username/password
2. System offers "Use recovery code" option
3. User enters recovery code
4. User optionally checks "Remember this device"
5. System validates and marks code as used
6. If remember_me: System creates TrustedDevice entry
7. System returns full tokens
8. User is logged in
9. System sends alert email about recovery code usage
```

#### Manage Trusted Devices Flow
```
1. User navigates to security settings
2. User views list of trusted devices (with device info, last used, expires date)
3. User can remove individual devices
4. System revokes trust for removed devices
5. Next login from that device requires 2FA
```

#### Download Recovery Codes Flow
```
1. User navigates to 2FA settings
2. User clicks "Download recovery codes"
3. User chooses format (TXT or PDF)
4. System generates file with recovery codes
5. System includes metadata (generated date, user info)
6. User downloads file
7. System logs the download event
```

### Security Considerations

1. **OTP Expiration**: 10 minutes for all OTP codes
2. **Rate Limiting**: 
   - Max 5 attempts per OTP code
   - Max 3 OTP requests per 15 minutes
   - Max 10 failed verifications per hour (account locked)
3. **Code Generation**: Cryptographically secure random 6-digit codes
4. **Recovery Codes**: 
   - 10 codes generated at setup
   - Single-use only
   - Can regenerate (invalidates old codes)
5. **Audit Logging**: All 2FA events logged with IP/user agent
6. **Partial Tokens**: Limited scope token returned before 2FA verification
7. **HTTPS Only**: All 2FA endpoints require HTTPS
8. **Phone Number Verification**: SMS method requires phone verification

### Configuration

```python
# mysite/mysite/settings.py (additions)

# 2FA Settings
TWOFA_ENABLED = env.bool('TWOFA_ENABLED', default=True)
TWOFA_CODE_LENGTH = 6
TWOFA_CODE_EXPIRY_MINUTES = 10
TWOFA_MAX_ATTEMPTS = 5
TWOFA_RATE_LIMIT_WINDOW = 900  # 15 minutes in seconds
TWOFA_RATE_LIMIT_MAX = 3
TWOFA_RECOVERY_CODE_COUNT = 10
TWOFA_ISSUER_NAME = 'Tinybeans'  # For TOTP QR codes

# Trusted Devices (Remember Me)
TWOFA_TRUSTED_DEVICE_ENABLED = env.bool('TWOFA_TRUSTED_DEVICE_ENABLED', default=True)
TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS = env.int('TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS', default=30)
TWOFA_TRUSTED_DEVICE_MAX_COUNT = env.int('TWOFA_TRUSTED_DEVICE_MAX_COUNT', default=5)  # Max devices per user

# SMS Provider Settings
SMS_PROVIDER = env.str('SMS_PROVIDER', default='twilio')  # 'twilio' or 'aws_sns'
TWILIO_ACCOUNT_SID = env.str('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env.str('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = env.str('TWILIO_PHONE_NUMBER', default='')
AWS_SNS_REGION = env.str('AWS_SNS_REGION', default='us-east-1')
```

### Python Dependencies

```python
# requirements.txt (additions)

pyotp==2.9.0              # TOTP implementation (RFC 6238)
qrcode==7.4.2             # QR code generation for TOTP setup
Pillow==10.1.0            # Image library (required by qrcode)
reportlab==4.0.7          # PDF generation for recovery codes
twilio==8.10.0            # Twilio SMS provider (optional)
boto3==1.29.7             # AWS SNS provider (optional)
```

### Database Migrations

```bash
# Create SMS app
python manage.py startapp sms

# Add to INSTALLED_APPS
# 'mysite.sms',

# Create migrations for auth models
python manage.py makemigrations auth

# Apply migrations
python manage.py migrate
```

### Testing Strategy

1. **Unit Tests**:
   - TOTP generation and validation
   - OTP generation and validation (email/SMS)
   - Recovery code generation and validation
   - QR code generation
   - PDF/TXT export functionality
   - Rate limiting logic
   - Provider implementations

2. **Integration Tests**:
   - Full TOTP setup flow
   - Full email/SMS setup flow
   - Full login flow with each 2FA method
   - Recovery code flow
   - Recovery code download (TXT/PDF)
   - Email/SMS delivery
   - Method switching

3. **E2E Tests**:
   - Complete user journey from signup → setup → login
   - Recovery scenarios
   - QR code scanning with real authenticator apps
   - Cross-device login

### Implementation Phases

#### Phase 1: Core Infrastructure (Week 1)
- Create SMS app structure
- Implement SMS provider interface
- Add 2FA models to auth app (including totp_secret field)
- Create base 2FA service
- Install TOTP dependencies (pyotp, qrcode)

#### Phase 2: TOTP Implementation (Week 2)
- Implement TOTP secret generation
- Implement QR code generation
- Add TOTP verification
- Create TOTP setup flow
- Test with Google Authenticator/Authy

#### Phase 3: Email/SMS 2FA (Week 3)
- Implement email-based OTP
- Implement SMS provider (Twilio)
- Add 2FA setup endpoints
- Create email templates
- Phone number verification

#### Phase 4: Recovery Codes (Week 4)
- Implement recovery code generation
- Add recovery code verification
- Implement TXT export
- Implement PDF export with reportlab
- Add download endpoint
- UI for downloading codes

#### Phase 5: Security & Polish (Week 5)
- Add rate limiting
- Audit logging
- Security hardening
- Frontend completion
- User documentation

#### Phase 5: Frontend & UX (Week 5)
- Complete frontend flows
- User settings UI
- Error handling & feedback
- User documentation

## Consequences

### Positive

1. **Enhanced Security**: Additional layer protecting user accounts
2. **TOTP Primary Method**: No delivery costs, works offline, industry standard
3. **Flexible Methods**: Users can choose from 3 2FA methods
4. **Modular Design**: SMS app is reusable for other SMS needs
5. **Existing Infrastructure**: Leverages current email system
6. **Recovery Options**: Downloadable recovery codes prevent lockouts
7. **Audit Trail**: Complete logging of security events
8. **User-friendly**: QR code setup, downloadable recovery codes
9. **No Vendor Lock-in**: Standard TOTP works with any authenticator app

### Negative

1. **Complexity**: Additional authentication step may frustrate some users
2. **SMS Costs**: Per-message charges for SMS delivery
3. **Support Burden**: Users may need help with setup/recovery
4. **TOTP Setup**: Requires authenticator app installation
5. **Development Time**: Significant feature requiring ~5 weeks
6. **Third-party Dependency**: SMS relies on Twilio/SNS availability
7. **Recovery Code Management**: Users must safely store recovery codes

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| SMS provider downtime | Fallback to email method |
| User loses phone/authenticator | Recovery codes downloadable as PDF/TXT |
| Recovery code loss | Support can disable 2FA with identity verification |
| Rate limit too strict | Adjustable via settings |
| Celery task failures | Retry logic + fallback to sync sending |
| QR code not scanning | Provide manual secret key entry option |
| User loses recovery codes | Generate new codes (invalidates old ones) |
| Device trust abuse | Configurable max devices, audit logging, email alerts |
| Cookie/device_id theft | Expire after X days, IP validation optional |

## Additional Features & Future Enhancements

### Implemented in ADR

1. **✅ Remember Me / Trusted Devices**
   - Skip 2FA on trusted devices for X days (default 30)
   - Device fingerprinting for identification
   - User can manage trusted devices list
   - Automatic cleanup of expired devices
   - Email notification when new device is trusted
   - Configurable max devices per user (default 5)

### Recommended Additional Features

2. **Backup Codes Refresh Reminder**
   - Notify users when they've used 50% of recovery codes
   - Prompt to generate new codes
   - Email reminder if only 2-3 codes remain

3. **2FA Method Switching**
   - Allow users to change preferred method
   - Requires verification with current method
   - Email notification of change
   - Audit log entry

4. **Grace Period for 2FA Disable**
   - 24-hour waiting period before 2FA fully disabled
   - Cancellable during grace period
   - Email confirmation required
   - Prevents accidental/unauthorized disabling

5. **Location-based Trust** (Optional Enhancement)
   - Trust devices by IP address range
   - Useful for office/home networks
   - Configurable geolocation rules
   - Alert on login from new location

6. **Biometric 2FA** (Mobile App Feature)
   - Fingerprint/Face ID on mobile
   - Push notification approval
   - No code typing needed
   - Requires mobile app development

7. **Emergency Access Codes** (Family Feature)
   - Designated family member can request access
   - Time-limited emergency codes
   - User notified immediately
   - Useful for incapacitation scenarios

8. **2FA Setup Wizard**
   - Step-by-step guided setup
   - Test verification before enabling
   - Download recovery codes step
   - Add trusted device option

9. **Admin Override/Disable** (Enterprise Feature)
   - Support staff can disable 2FA with proper authentication
   - Requires admin credentials + user identity verification
   - Audit log with justification
   - User notified via email

10. **Session Isolation**
    - Device-specific sessions
    - Logout from specific device
    - "Logout all devices" option
    - Session activity monitoring

11. **Progressive Enrollment**
    - Optional 2FA initially
    - Mandatory after accessing sensitive features
    - Gentle reminders to enable
    - Automatic enrollment for high-value accounts

12. **Suspicious Activity Detection**
    - Impossible travel detection (login from distant locations)
    - Login time pattern analysis
    - Force 2FA even on trusted devices if suspicious
    - Email/SMS alert

13. **Backup Email Verification**
    - Add backup email for 2FA codes
    - Useful when primary email unavailable
    - Must be verified separately
    - Used for recovery and alerts

14. **Webhook/API for 2FA Events**
    - External system integration
    - Real-time 2FA event notifications
    - Third-party SIEM integration
    - Compliance reporting

15. **2FA Analytics Dashboard**
    - Success/failure rates
    - Method preferences by user
    - Device trust statistics
    - Security incident detection

### Security Enhancements (Nice to Have)

16. **IP Address Validation on Trusted Devices**
    - Optionally bind trusted device to IP range
    - Alert if device_id used from different IP
    - Useful for static IP environments

17. **Hardware Security Key Support (WebAuthn)**
    - YubiKey, Titan Key support
    - Most secure option
    - Future Phase 6 enhancement

18. **Time-based Device Trust**
    - Different trust durations based on risk
    - Public networks: 1 day
    - Home network: 30 days
    - Configurable per user preference

19. **Anomaly Detection**
    - Machine learning for login patterns
    - Flag unusual behavior
    - Adaptive authentication (step-up challenges)

20. **Multi-device TOTP Sync** (Advanced)
    - Encrypted TOTP secret backup
    - Restore on new device
    - Cloud backup with encryption
    - Complex implementation

### UX Improvements

21. **Remember Device Prompt Timing**
    - Show checkbox during 2FA entry
    - Post-login prompt option
    - User preference saved

22. **Quick Trust Toggle**
    - "Always require 2FA" mode
    - Disable device trust temporarily
    - For high-security situations

23. **2FA Method Recommendations**
    - Suggest TOTP for best security
    - Explain pros/cons of each method
    - Show what others choose

24. **Inline Recovery Code Display**
    - Show codes immediately after setup
    - Force user to save/download
    - Checkbox: "I have saved these codes"

25. **Mobile-First 2FA Experience**
    - Optimized for mobile browsers
    - Auto-copy codes from SMS
    - Native app integration

## Alternatives Considered

### 1. TOTP (Time-based One-Time Password)
**Pros**: No delivery cost, works offline, standard protocol (Google Authenticator, Authy)
**Cons**: Requires separate app, more complex setup, harder for non-technical users
**Decision**: ✅ **ACCEPTED** - Implemented as primary method

### 2. WebAuthn/FIDO2 (Hardware keys)
**Pros**: Most secure, phishing-resistant
**Cons**: Requires hardware, complex implementation, low user adoption
**Decision**: Future consideration for enterprise tier

### 3. Email-only 2FA
**Pros**: Simple, no additional costs, existing infrastructure
**Cons**: Less secure if email compromised, limited options
**Decision**: Rejected - want to offer multiple methods

### 4. Third-party 2FA Service (Auth0, Okta)
**Pros**: Fully managed, battle-tested, all methods included
**Cons**: High cost, vendor lock-in, data privacy concerns
**Decision**: Rejected - prefer in-house control

## References

- [OWASP Multi-Factor Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)
- [NIST SP 800-63B: Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [RFC 6238: TOTP Algorithm](https://datatracker.ietf.org/doc/html/rfc6238)
- [PyOTP Documentation](https://pyotp.readthedocs.io/)
- [Twilio SMS API Documentation](https://www.twilio.com/docs/sms)
- [Django Custom Authentication](https://docs.djangoproject.com/en/stable/topics/auth/customizing/)

## Appendix A: API Request/Response Examples

### Setup 2FA (TOTP - Authenticator App)
```http
POST /api/auth/2fa/setup/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "method": "totp"
}

Response 200:
{
  "method": "totp",
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "otpauth://totp/Tinybeans:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Tinybeans",
  "qr_code_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEU...",
  "message": "Scan QR code with your authenticator app"
}
```

### Setup 2FA (Email/SMS)
```http
POST /api/auth/2fa/setup/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "method": "email",
  "phone_number": "+1234567890"  // Required if method is 'sms'
}

Response 200:
{
  "message": "Verification code sent to your email",
  "method": "email",
  "expires_in": 600
}
```

### Verify Setup
```http
POST /api/auth/2fa/verify-setup/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "code": "123456"
}

Response 200:
{
  "enabled": true,
  "method": "totp",
  "recovery_codes": [
    "ABCD-EFGH-IJKL",
    "MNOP-QRST-UVWX",
    "1234-5678-9012",
    ...  // 10 codes total
  ]
}
```

### Download Recovery Codes
```http
GET /api/auth/2fa/recovery-codes/download/?format=txt
Authorization: Bearer <access_token>

Response 200:
Content-Type: text/plain
Content-Disposition: attachment; filename="tinybeans-recovery-codes.txt"

Tinybeans Recovery Codes
Generated: 2024-10-01 14:30:00 UTC
User: user@example.com

Keep these codes in a safe place. Each code can only be used once.

1. ABCD-EFGH-IJKL
2. MNOP-QRST-UVWX
3. 1234-5678-9012
4. AAAA-BBBB-CCCC
5. DDDD-EEEE-FFFF
6. GGGG-HHHH-IIII
7. JJJJ-KKKK-LLLL
8. MMMM-NNNN-OOOO
9. PPPP-QQQQ-RRRR
10. SSSS-TTTT-UUUU
```

```http
GET /api/auth/2fa/recovery-codes/download/?format=pdf
Authorization: Bearer <access_token>

Response 200:
Content-Type: application/pdf
Content-Disposition: attachment; filename="tinybeans-recovery-codes.pdf"

[PDF file with formatted recovery codes]
```

### Login (2FA enabled)
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}

Response 200:
{
  "requires_2fa": true,
  "partial_token": "eyJ0eXAi...",
  "method": "totp",  // or "email" or "sms"
  "message": "Enter code from your authenticator app"
}
```

### Verify Login
```http
POST /api/auth/2fa/verify/
Content-Type: application/json
Authorization: Bearer <partial_token>

{
  "code": "123456"
}

Response 200:
{
  "tokens": {
    "access": "eyJ0eXAi...",
    "refresh": "eyJ0eXAi..."
  },
  "user": { ... }
}
```

## Appendix B: Email Template Example

```html
<!-- mysite/emails/templates/emails/2fa_code.html -->
<!DOCTYPE html>
<html>
<head>
  <title>Your Verification Code</title>
</head>
<body>
  <h1>Your Verification Code</h1>
  <p>Hello {{ user.username }},</p>
  
  <p>Your verification code is:</p>
  <h2 style="font-size: 32px; letter-spacing: 8px; font-family: monospace;">
    {{ code }}
  </h2>
  
  <p>This code will expire in 10 minutes.</p>
  
  <p>If you didn't request this code, please ignore this email or contact support if you're concerned about your account security.</p>
  
  <p>Best regards,<br>The Tinybeans Team</p>
</body>
</html>
```

## Appendix C: Code Implementation Examples

### TOTP Secret Generation and QR Code

```python
# mysite/auth/services/twofa_service.py

import pyotp
import qrcode
import io
import base64
from django.conf import settings

class TwoFactorService:
    
    @staticmethod
    def generate_totp_secret() -> str:
        """Generate a new TOTP secret (base32 encoded)"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_totp_qr_code(user, secret: str) -> dict:
        """
        Generate QR code for TOTP setup
        Returns dict with URI and base64 image
        """
        # Create otpauth URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.TWOFA_ISSUER_NAME
        )
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'uri': uri,
            'qr_code_image': f'data:image/png;base64,{img_str}',
            'secret': secret
        }
    
    @staticmethod
    def verify_totp(user, code: str) -> bool:
        """Verify TOTP code from authenticator app"""
        try:
            settings = user.twofa_settings
            if not settings.totp_secret:
                return False
            
            totp = pyotp.TOTP(settings.totp_secret)
            # Allow 1 time step (30s) drift in either direction
            return totp.verify(code, valid_window=1)
        except Exception:
            return False
```

### Recovery Code Export (TXT and PDF)

```python
# mysite/auth/services/recovery_code_service.py

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.units import inch
from django.utils import timezone
import io

class RecoveryCodeService:
    
    @staticmethod
    def export_as_txt(user, recovery_codes: list) -> str:
        """Export recovery codes as plain text"""
        lines = [
            "Tinybeans Recovery Codes",
            "=" * 50,
            f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"User: {user.email}",
            "",
            "Keep these codes in a safe place. Each code can only be used once.",
            "",
        ]
        
        for i, code in enumerate(recovery_codes, 1):
            lines.append(f"{i:2d}. {code.code}")
        
        lines.extend([
            "",
            "IMPORTANT:",
            "- Store these codes securely",
            "- Each code works only once",
            "- Generate new codes if these are lost",
            "- Contact support if you need help",
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def export_as_pdf(user, recovery_codes: list) -> bytes:
        """Export recovery codes as PDF"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph("Tinybeans Recovery Codes", styles['Heading1'])
        story.append(title)
        story.append(Spacer(1, 0.3*inch))
        
        # Info
        info_text = f"""
        <b>Generated:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}<br/>
        <b>User:</b> {user.email}<br/>
        <br/>
        Keep these codes in a safe place. Each code can only be used once.
        """
        info = Paragraph(info_text, styles['Normal'])
        story.append(info)
        story.append(Spacer(1, 0.5*inch))
        
        # Recovery codes table
        data = [['#', 'Recovery Code']]
        for i, code in enumerate(recovery_codes, 1):
            data.append([str(i), code.code])
        
        table = Table(data, colWidths=[0.5*inch, 3*inch])
        table.setStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#cccccc'),
            ('TEXTCOLOR', (0, 0), (-1, 0), '#000000'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, '#000000'),
        ])
        story.append(table)
        story.append(Spacer(1, 0.5*inch))
        
        # Important notes
        notes = Paragraph("""
        <b>IMPORTANT:</b><br/>
        • Store these codes securely (password manager, safe, etc.)<br/>
        • Each code works only once<br/>
        • Generate new codes if these are lost<br/>
        • Contact support if you need help<br/>
        """, styles['Normal'])
        story.append(notes)
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
```

### Recovery Code Download View

```python
# mysite/auth/views.py

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services.recovery_code_service import RecoveryCodeService

class RecoveryCodeDownloadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Download recovery codes in TXT or PDF format"""
        format_type = request.query_params.get('format', 'txt')
        user = request.user
        
        # Get unused recovery codes
        recovery_codes = user.recovery_codes.filter(is_used=False)
        
        if not recovery_codes.exists():
            return Response(
                {'error': 'No recovery codes available. Generate new codes first.'},
                status=400
            )
        
        if format_type == 'pdf':
            pdf_bytes = RecoveryCodeService.export_as_pdf(user, recovery_codes)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="tinybeans-recovery-codes.pdf"'
        else:
            txt_content = RecoveryCodeService.export_as_txt(user, recovery_codes)
            response = HttpResponse(txt_content, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="tinybeans-recovery-codes.txt"'
        
        # Log the download
        TwoFactorAuditLog.objects.create(
            user=user,
            action='recovery_codes_downloaded',
            method=format_type,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True
        )
        
        return response
```

### Frontend QR Code Display (React)

```tsx
// web/src/modules/auth/components/TotpSetup.tsx

import { useState } from 'react'
import { api } from '../client'

export function TotpSetup() {
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [secret, setSecret] = useState<string>('')
  const [verificationCode, setVerificationCode] = useState('')

  const initializeSetup = async () => {
    const response = await api.post('/auth/2fa/setup/', { method: 'totp' })
    setQrCode(response.qr_code_image)
    setSecret(response.secret)
  }

  const verifySetup = async () => {
    await api.post('/auth/2fa/verify-setup/', { code: verificationCode })
    // Show recovery codes...
  }

  return (
    <div className="totp-setup">
      <h2>Set up Authenticator App</h2>
      
      {!qrCode ? (
        <button onClick={initializeSetup}>Start Setup</button>
      ) : (
        <>
          <div className="qr-code">
            <img src={qrCode} alt="QR Code" />
            <p>Scan this with your authenticator app</p>
          </div>
          
          <div className="manual-entry">
            <p>Or enter this code manually:</p>
            <code>{secret}</code>
          </div>
          
          <div className="verification">
            <input
              type="text"
              placeholder="Enter 6-digit code"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              maxLength={6}
            />
            <button onClick={verifySetup}>Verify & Enable</button>
          </div>
        </>
      )}
    </div>
  )
}
```

### Trusted Device Implementation (Remember Me)

```python
# mysite/auth/services/trusted_device_service.py

import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

class TrustedDeviceService:
    
    @staticmethod
    def generate_device_id(request) -> str:
        """
        Generate unique device identifier from browser fingerprint
        Combines user agent, accept headers, and random salt
        """
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        
        # Create fingerprint
        fingerprint = f"{user_agent}|{accept_language}|{accept_encoding}"
        
        # Add random salt for uniqueness
        salt = secrets.token_urlsafe(16)
        combined = f"{fingerprint}|{salt}"
        
        # Hash to create device_id
        device_id = hashlib.sha256(combined.encode()).hexdigest()
        
        return device_id
    
    @staticmethod
    def get_device_name(request) -> str:
        """Extract readable device name from user agent"""
        from user_agents import parse
        
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        ua = parse(user_agent)
        
        browser = f"{ua.browser.family} {ua.browser.version_string}"
        os = f"{ua.os.family} {ua.os.version_string}"
        device = ua.device.family
        
        if device == 'Other':
            return f"{browser} on {os}"
        return f"{browser} on {device} ({os})"
    
    @staticmethod
    def add_trusted_device(user, request, days=None) -> TrustedDevice:
        """Add current device to trusted devices list"""
        if days is None:
            days = settings.TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS
        
        device_id = TrustedDeviceService.generate_device_id(request)
        device_name = TrustedDeviceService.get_device_name(request)
        ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check if user has too many trusted devices
        existing_count = TrustedDevice.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).count()
        
        if existing_count >= settings.TWOFA_TRUSTED_DEVICE_MAX_COUNT:
            # Remove oldest device
            oldest = TrustedDevice.objects.filter(
                user=user,
                expires_at__gt=timezone.now()
            ).order_by('created_at').first()
            if oldest:
                oldest.delete()
        
        # Create or update trusted device
        trusted_device, created = TrustedDevice.objects.update_or_create(
            user=user,
            device_id=device_id,
            defaults={
                'device_name': device_name,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'expires_at': timezone.now() + timedelta(days=days),
            }
        )
        
        # Send notification email
        if created:
            from mysite.emailing.mailers import TwoFactorMailer
            TwoFactorMailer.send_trusted_device_added(user, trusted_device)
        
        # Log the action
        TwoFactorAuditLog.objects.create(
            user=user,
            action='trusted_device_added',
            method='device_trust',
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id,
            success=True
        )
        
        return trusted_device
    
    @staticmethod
    def is_trusted_device(user, device_id) -> bool:
        """Check if device is trusted and not expired"""
        try:
            device = TrustedDevice.objects.get(
                user=user,
                device_id=device_id,
                expires_at__gt=timezone.now()
            )
            # Update last_used_at
            device.last_used_at = timezone.now()
            device.save(update_fields=['last_used_at'])
            return True
        except TrustedDevice.DoesNotExist:
            return False
    
    @staticmethod
    def get_device_id_from_request(request) -> str:
        """Extract device_id from request (cookie or header)"""
        # Try cookie first
        device_id = request.COOKIES.get('device_id')
        if device_id:
            return device_id
        
        # Try header
        device_id = request.META.get('HTTP_X_DEVICE_ID')
        return device_id
    
    @staticmethod
    def remove_trusted_device(user, device_id) -> bool:
        """Remove device from trusted list"""
        try:
            device = TrustedDevice.objects.get(user=user, device_id=device_id)
            device.delete()
            
            # Log the removal
            TwoFactorAuditLog.objects.create(
                user=user,
                action='trusted_device_removed',
                method='device_trust',
                device_id=device_id,
                success=True
            )
            
            return True
        except TrustedDevice.DoesNotExist:
            return False
    
    @staticmethod
    def get_trusted_devices(user):
        """Get all active trusted devices for user"""
        return TrustedDevice.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).order_by('-last_used_at')
    
    @staticmethod
    def cleanup_expired_devices():
        """Clean up expired trusted devices (run as scheduled task)"""
        expired_count = TrustedDevice.objects.filter(
            expires_at__lte=timezone.now()
        ).delete()[0]
        
        return expired_count
```

### Enhanced Login View with Trusted Device Support

```python
# mysite/auth/views.py

from rest_framework.response import Response
from rest_framework import status
from .services.trusted_device_service import TrustedDeviceService

class TwoFactorVerifyView(APIView):
    """Verify 2FA code with optional remember device"""
    permission_classes = [IsAuthenticated]  # Requires partial token
    
    def post(self, request):
        user = request.user
        code = request.data.get('code')
        remember_me = request.data.get('remember_me', False)
        
        if not code:
            return Response(
                {'error': 'Verification code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the code (TOTP, OTP, or recovery code)
        settings = user.twofa_settings
        verified = False
        
        if settings.preferred_method == 'totp':
            verified = TwoFactorService.verify_totp(user, code)
        else:
            verified = TwoFactorService.verify_otp(user, code, purpose='login')
        
        if not verified:
            # Try recovery code
            verified = TwoFactorService.verify_recovery_code(user, code)
        
        if not verified:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate full tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        response_data = {
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
        }
        
        # Handle remember device
        if remember_me and settings.TWOFA_TRUSTED_DEVICE_ENABLED:
            trusted_device = TrustedDeviceService.add_trusted_device(user, request)
            response_data['device_id'] = trusted_device.device_id
            response_data['device_trust_expires'] = trusted_device.expires_at.isoformat()
        
        # Create response with cookies if remember_me
        response = Response(response_data, status=status.HTTP_200_OK)
        
        if remember_me and 'device_id' in response_data:
            # Set device_id cookie
            response.set_cookie(
                key='device_id',
                value=response_data['device_id'],
                max_age=settings.TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS * 24 * 60 * 60,
                httponly=True,
                secure=True,  # HTTPS only
                samesite='Lax'
            )
        
        # Log successful verification
        TwoFactorAuditLog.objects.create(
            user=user,
            action='2fa_verified',
            method=settings.preferred_method,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            device_id=response_data.get('device_id', ''),
            success=True
        )
        
        return response


class LoginView(APIView):
    """Enhanced login with trusted device check"""
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        # Authenticate user
        from django.contrib.auth import authenticate
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if 2FA is enabled
        try:
            settings = user.twofa_settings
            if not settings.is_enabled:
                # No 2FA, return full tokens
                from rest_framework_simplejwt.tokens import RefreshToken
                refresh = RefreshToken.for_user(user)
                return Response({
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    },
                    'user': {'id': user.id, 'username': user.username}
                })
        except:
            # No 2FA settings, return full tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            return Response({
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
                'user': {'id': user.id, 'username': user.username}
            })
        
        # Check if device is trusted
        if settings.TWOFA_TRUSTED_DEVICE_ENABLED:
            device_id = TrustedDeviceService.get_device_id_from_request(request)
            if device_id and TrustedDeviceService.is_trusted_device(user, device_id):
                # Trusted device, skip 2FA
                from rest_framework_simplejwt.tokens import RefreshToken
                refresh = RefreshToken.for_user(user)
                
                # Log the trusted device login
                TwoFactorAuditLog.objects.create(
                    user=user,
                    action='trusted_device_login',
                    method='device_trust',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    device_id=device_id,
                    success=True
                )
                
                return Response({
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    },
                    'user': {'id': user.id, 'username': user.username},
                    'skipped_2fa': True,
                    'reason': 'trusted_device'
                })
        
        # 2FA required, send code if needed
        if settings.preferred_method in ['email', 'sms']:
            TwoFactorService.send_otp(user, method=settings.preferred_method, purpose='login')
        
        # Generate partial token
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        # Add custom claim to mark as partial
        refresh['is_partial'] = True
        partial_token = str(refresh.access_token)
        
        return Response({
            'requires_2fa': True,
            'partial_token': partial_token,
            'method': settings.preferred_method,
            'message': f'Enter code from your {settings.get_preferred_method_display()}'
        })


class TrustedDevicesListView(APIView):
    """List and manage trusted devices"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all trusted devices"""
        devices = TrustedDeviceService.get_trusted_devices(request.user)
        
        data = [{
            'device_id': d.device_id,
            'device_name': d.device_name,
            'ip_address': d.ip_address,
            'last_used_at': d.last_used_at.isoformat(),
            'expires_at': d.expires_at.isoformat(),
            'created_at': d.created_at.isoformat(),
        } for d in devices]
        
        return Response({'devices': data})
    
    def delete(self, request):
        """Remove a trusted device"""
        device_id = request.data.get('device_id')
        
        if not device_id:
            return Response(
                {'error': 'device_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        removed = TrustedDeviceService.remove_trusted_device(request.user, device_id)
        
        if removed:
            return Response({'message': 'Device removed successfully'})
        else:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
```

### Celery Task for Cleanup

```python
# mysite/auth/tasks.py

from celery import shared_task
from .services.trusted_device_service import TrustedDeviceService

@shared_task
def cleanup_expired_trusted_devices():
    """
    Scheduled task to clean up expired trusted devices
    Run daily via celery beat
    """
    expired_count = TrustedDeviceService.cleanup_expired_devices()
    return f"Cleaned up {expired_count} expired trusted devices"
```

### Celery Beat Configuration

```python
# mysite/mysite/settings.py

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-trusted-devices': {
        'task': 'mysite.auth.tasks.cleanup_expired_trusted_devices',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}
```

### Frontend Remember Me Component

```tsx
// web/src/modules/auth/components/TwoFactorVerify.tsx

import { useState } from 'react'
import { api } from '../client'

export function TwoFactorVerify({ partialToken, method }) {
  const [code, setCode] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleVerify = async () => {
    setLoading(true)
    try {
      const response = await api.post(
        '/auth/2fa/verify/',
        {
          code,
          remember_me: rememberMe
        },
        {
          headers: {
            Authorization: `Bearer ${partialToken}`
          }
        }
      )
      
      // Store device_id if returned
      if (response.device_id) {
        // Cookie is already set by backend
        console.log('Device trusted for 30 days')
      }
      
      // Store tokens and redirect
      localStorage.setItem('access_token', response.tokens.access)
      localStorage.setItem('refresh_token', response.tokens.refresh)
      window.location.href = '/'
      
    } catch (error) {
      alert('Invalid code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="2fa-verify">
      <h2>Two-Factor Authentication</h2>
      <p>Enter the code from your {method}</p>
      
      <input
        type="text"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="000000"
        maxLength={6}
      />
      
      <label>
        <input
          type="checkbox"
          checked={rememberMe}
          onChange={(e) => setRememberMe(e.target.checked)}
        />
        Remember this device for 30 days
      </label>
      
      <button onClick={handleVerify} disabled={loading || code.length !== 6}>
        {loading ? 'Verifying...' : 'Verify'}
      </button>
      
      <p className="trust-info">
        ℹ️ Trusting this device will skip 2FA on future logins from this browser.
        You can manage trusted devices in your security settings.
      </p>
    </div>
  )
}
```


