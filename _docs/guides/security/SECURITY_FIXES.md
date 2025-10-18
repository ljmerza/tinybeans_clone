# 🔧 Security Fixes Guide

Quick implementation guide for the 3 high-priority security fixes identified in the audit.

---

## Fix 1: Encrypt TOTP Secrets (4 hours)

### Step 1: Install cryptography
```bash
pip install cryptography
pip freeze > requirements/base.txt
```

### Step 2: Generate encryption key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 3: Add to settings
```python
# mysite/settings/base.py
import os

# SECURITY WARNING: Keep this secret in production!
TWOFA_ENCRYPTION_KEY = os.environ.get(
    'TWOFA_ENCRYPTION_KEY',
    'your-generated-key-here'  # Replace with generated key
)
```

### Step 4: Update model
```python
# mysite/auth/models.py
from django.conf import settings
from cryptography.fernet import Fernet

class TwoFactorSettings(models.Model):
    _totp_secret_encrypted = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_column='totp_secret'
    )
    
    @property
    def totp_secret(self):
        """Decrypt and return TOTP secret"""
        if not self._totp_secret_encrypted:
            return None
        try:
            cipher = Fernet(settings.TWOFA_ENCRYPTION_KEY.encode())
            return cipher.decrypt(self._totp_secret_encrypted.encode()).decode()
        except Exception:
            return None
    
    @totp_secret.setter
    def totp_secret(self, value):
        """Encrypt and store TOTP secret"""
        if value:
            cipher = Fernet(settings.TWOFA_ENCRYPTION_KEY.encode())
            self._totp_secret_encrypted = cipher.encrypt(value.encode()).decode()
        else:
            self._totp_secret_encrypted = None
```

### Step 5: Create data migration
```bash
python manage.py makemigrations auth --empty --name encrypt_totp_secrets
```

```python
# Generated migration file
from django.db import migrations
from cryptography.fernet import Fernet
from django.conf import settings

def encrypt_existing_secrets(apps, schema_editor):
    TwoFactorSettings = apps.get_model('auth', 'TwoFactorSettings')
    cipher = Fernet(settings.TWOFA_ENCRYPTION_KEY.encode())
    
    for setting in TwoFactorSettings.objects.filter(totp_secret__isnull=False):
        if setting.totp_secret and len(setting.totp_secret) == 32:
            # Encrypt plain text secret
            encrypted = cipher.encrypt(setting.totp_secret.encode()).decode()
            setting.totp_secret = encrypted
            setting.save(update_fields=['totp_secret'])

def decrypt_secrets(apps, schema_editor):
    # Reverse migration
    TwoFactorSettings = apps.get_model('auth', 'TwoFactorSettings')
    cipher = Fernet(settings.TWOFA_ENCRYPTION_KEY.encode())
    
    for setting in TwoFactorSettings.objects.filter(totp_secret__isnull=False):
        try:
            decrypted = cipher.decrypt(setting.totp_secret.encode()).decode()
            setting.totp_secret = decrypted
            setting.save(update_fields=['totp_secret'])
        except Exception:
            pass

class Migration(migrations.Migration):
    dependencies = [
        ('auth', 'previous_migration'),
    ]
    
    operations = [
        migrations.RunPython(encrypt_existing_secrets, decrypt_secrets),
    ]
```

### Step 6: Run migration
```bash
python manage.py migrate auth
```

---

## Fix 2: Hash Recovery Codes (3 hours)

### Step 1: Update model
```python
# mysite/auth/models.py
import hashlib

class RecoveryCode(models.Model):
    code_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hash
    # Remove: code = models.CharField(max_length=16, unique=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Step 2: Create migration
```bash
python manage.py makemigrations auth
```

### Step 3: Update service
```python
# mysite/auth/services/twofa_service.py
import hashlib

class TwoFactorService:
    @staticmethod
    def generate_recovery_codes(user, count=10) -> tuple:
        """Generate recovery codes and return both objects and plain codes"""
        RecoveryCode.objects.filter(user=user, is_used=False).delete()
        
        codes = []
        plain_codes = []  # For user display only
        
        for _ in range(count):
            plain_code = '-'.join(
                ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                        for _ in range(4))
                for _ in range(3)
            )
            
            # Hash the code
            code_hash = hashlib.sha256(plain_code.encode()).hexdigest()
            
            recovery_code = RecoveryCode.objects.create(
                user=user,
                code_hash=code_hash
            )
            
            codes.append(recovery_code)
            plain_codes.append(plain_code)
        
        return codes, plain_codes
    
    @staticmethod
    def verify_recovery_code(user, plain_code) -> bool:
        """Verify recovery code by comparing hash"""
        try:
            code_hash = hashlib.sha256(plain_code.upper().encode()).hexdigest()
            
            recovery_code = RecoveryCode.objects.filter(
                user=user,
                code_hash=code_hash,
                is_used=False
            ).first()
            
            if not recovery_code:
                return False
            
            recovery_code.is_used = True
            recovery_code.used_at = timezone.now()
            recovery_code.save()
            
            # Send alert
            from mysite.emails.mailers import TwoFactorMailer
            TwoFactorMailer.send_recovery_code_used_alert(user, recovery_code)
            
            return True
        except Exception:
            return False
```

### Step 4: Update views
```python
# mysite/auth/views_2fa.py

class RecoveryCodeGenerateView(APIView):
    def post(self, request):
        # ... existing code ...
        
        # Updated call returns both
        recovery_codes, plain_codes = TwoFactorService.generate_recovery_codes(user)
        
        return Response({
            'codes': plain_codes,  # Send plain codes to user (only time shown)
            'count': len(plain_codes)
        })
```

---

## Fix 3: Add Login Rate Limiting (2 hours)

### Step 1: Install django-ratelimit
```bash
pip install django-ratelimit
pip freeze > requirements/base.txt
```

### Step 2: Add to settings
```python
# mysite/settings/base.py

# Rate limiting
RATELIMIT_ENABLE = not DEBUG
RATELIMIT_USE_CACHE = 'default'
```

### Step 3: Update LoginView
```python
# mysite/auth/views.py
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from django.core.cache import cache

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer
    
    @extend_schema(...)
    @method_decorator(ratelimit(key='ip', rate='10/h', block=False))
    @method_decorator(ratelimit(key='user_or_ip', rate='5/h', block=False))
    def post(self, request):
        # Check if rate limited
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            return Response(
                {'error': 'Too many login attempts. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # ... rest of existing code ...
```

### Step 4: Create custom rate limit key
```python
# mysite/auth/ratelimit.py (new file)

def user_or_ip(group, request):
    """Rate limit key: username if provided, else IP"""
    username = request.POST.get('username') or request.data.get('username')
    if username:
        return f'user:{username}'
    return request.META.get('REMOTE_ADDR', 'unknown')
```

### Step 5: Update view with custom key
```python
from .ratelimit import user_or_ip

@method_decorator(ratelimit(key=user_or_ip, rate='5/h', block=False))
def post(self, request):
    # ... existing code
```

---

## Testing the Fixes

### Test 1: TOTP Encryption
```python
# Create test
from mysite.auth.models import TwoFactorSettings
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

settings = TwoFactorSettings.objects.create(
    user=user,
    totp_secret='JBSWY3DPEHPK3PXP'
)

# Check database - should see encrypted value
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT totp_secret FROM auth_twofactorsettings WHERE user_id=%s", [user.id])
print(cursor.fetchone())  # Should show encrypted string

# Check property - should return plain text
print(settings.totp_secret)  # Should show 'JBSWY3DPEHPK3PXP'
```

### Test 2: Recovery Code Hashing
```python
from mysite.auth.services.twofa_service import TwoFactorService

codes, plain_codes = TwoFactorService.generate_recovery_codes(user)

# Verify first code
assert TwoFactorService.verify_recovery_code(user, plain_codes[0]) == True

# Try to use again (should fail)
assert TwoFactorService.verify_recovery_code(user, plain_codes[0]) == False

# Check database - should see hash
from mysite.auth.models import RecoveryCode
code = RecoveryCode.objects.first()
print(code.code_hash)  # Should show SHA-256 hash
```

### Test 3: Rate Limiting
```bash
# Test with curl
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/auth/login/ \
    -d '{"username":"test","password":"wrong"}' \
    -H "Content-Type: application/json"
  echo "Attempt $i"
done

# Should see 429 after 10 attempts
```

---

## Deployment Checklist

- [ ] All 3 fixes implemented
- [ ] Unit tests updated
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Environment variables set in production
- [ ] TWOFA_ENCRYPTION_KEY in production env
- [ ] Cache configured for rate limiting
- [ ] Backup database before migration
- [ ] Run migrations in staging first
- [ ] Monitor error logs after deployment
- [ ] Document encryption key backup procedure

---

## Rollback Plan

### If encryption causes issues:
1. Revert migration: `python manage.py migrate auth <previous_migration>`
2. Update code to use old field
3. Deploy code fix
4. Re-run migration when ready

### If rate limiting too strict:
1. Adjust rates in decorator: `rate='20/h'`
2. Or disable: `RATELIMIT_ENABLE = False` in settings

### If recovery code hashing fails:
1. Keep both fields temporarily
2. Migrate gradually
3. Remove old field after verification

---

## Timeline

| Fix | Estimated Time | Priority |
|-----|----------------|----------|
| TOTP Encryption | 4 hours | HIGH |
| Recovery Code Hashing | 3 hours | HIGH |
| Login Rate Limiting | 2 hours | MEDIUM |
| **Total** | **9 hours** | **1-2 days** |

---

## Success Metrics

After implementing fixes:

- Security score: 82% → 90%+
- OWASP A02 (Cryptographic Failures): ⚠️ → ✅
- OWASP A07 (Auth Failures): ⚠️ → ✅
- Database compromise impact: HIGH → LOW
- Brute force protection: PARTIAL → COMPLETE

---

## Questions?

See full audit: `docs/SECURITY_AUDIT.md`

Contact: security@tinybeans.com
