# Partner Authentication System

> **Version:** 2.1  
> **Last Updated:** 2026-01-24  
> **Status:** Aligned with schema.md v1.1 (all clarifications applied)

---

## Overview

Password-based authentication for Partner Dashboard (Franchise & Revenue Vendor). Unlike user app (OTP-based), partners use password authentication similar to admin.

**Key Principle:** Partners are existing `users_user` records linked to `partners` table via `user_id`.

---

## Schema Alignment

### partners table (from schema.md)

Auth system uses these fields from `partners` table:

| Field | Type | Auth Usage |
|-------|------|------------|
| `user_id` | BIGINT FK | Links to `users_user` for password storage |
| `partner_type` | VARCHAR(20) | `FRANCHISE` or `VENDOR` |
| `vendor_type` | VARCHAR(20) | `REVENUE` or `NON_REVENUE` (dashboard access) |
| `status` | VARCHAR(20) | `ACTIVE`, `INACTIVE`, `SUSPENDED` |
| `business_name` | VARCHAR(100) | Display name in login response |
| `code` | VARCHAR(20) | Partner code (FR-001, VN-001) |
| `contact_email` | VARCHAR(255) | Primary email for auth |

### users_user table modifications

Add field to enable password for partners:

```sql
ALTER TABLE users_user ADD COLUMN is_partner BOOLEAN NOT NULL DEFAULT FALSE;
```

**Password Method Update** (in `User` model):
```python
def set_password(self, raw_password):
    if self.is_staff or self.is_superuser or self.is_partner:
        super().set_password(raw_password)

def check_password(self, raw_password):
    if self.is_staff or self.is_superuser or self.is_partner:
        return super().check_password(raw_password)
    return False
```

### Redis Token Storage

```
# Password Setup Token (24h)
Key: partner:setup:{token}
Value: {"partner_id": "uuid", "user_id": 123, "email": "x@y.com"}
TTL: 86400

# Password Reset Token (1h)
Key: partner:reset:{token}
Value: {"partner_id": "uuid", "user_id": 123, "email": "x@y.com"}
TTL: 3600
```

---

## Authentication Flows

### Flow 1: Partner Account Creation

```
Admin Dashboard
      │
      ▼
POST /api/admin/partners/franchise/  OR
POST /api/admin/partners/vendor/
      │
      ▼
┌─────────────────────────────────────┐
│ PartnerService.create_partner()     │
│                                     │
│ 1. Validate user_id exists          │
│ 2. Check user not already partner   │
│ 3. Create partners record           │
│ 4. Set users_user.is_partner=TRUE   │
│ 5. Generate setup token (UUID)      │
│ 6. Store in Redis (24h TTL)         │
│ 7. Send invitation email            │
└─────────────────────────────────────┘
      │
      ▼
Email: "Set password at: https://partners.chargeghar.com/setup/{token}"
```

### Flow 2: Initial Password Setup

```
Partner clicks email link
      │
      ▼
POST /api/partners/auth/set-password
{
  "token": "uuid",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
      │
      ▼
┌─────────────────────────────────────┐
│ PartnerAuthService.set_password()   │
│                                     │
│ 1. Validate token from Redis        │
│ 2. Get partner_id from token data   │
│ 3. Validate password strength       │
│ 4. Set password on users_user       │
│ 5. Clear token from Redis           │
│ 6. Generate JWT tokens              │
└─────────────────────────────────────┘
      │
      ▼
Response: { access_token, refresh_token, partner }
```

### Flow 3: Partner Login

```
POST /api/partners/auth/login
{
  "email": "abc@example.com",
  "password": "SecurePass123!"
}
      │
      ▼
┌─────────────────────────────────────┐
│ PartnerAuthService.login()          │
│                                     │
│ 1. Get user by email + is_partner   │
│ 2. Get partner by user_id           │
│ 3. Check partner.status == 'ACTIVE' │
│ 4. Check vendor_type != NON_REVENUE │
│    (or partner_type == FRANCHISE)   │
│ 5. Verify password                  │
│ 6. Update users_user.last_login     │
│ 7. Generate JWT tokens              │
└─────────────────────────────────────┘
      │
      ▼
Response:
{
  "access_token": "...",
  "refresh_token": "...",
  "partner": {
    "id": "uuid",
    "partner_type": "FRANCHISE",
    "vendor_type": null,
    "code": "FR-001",
    "business_name": "ABC Franchise",
    "status": "ACTIVE"
  }
}
```

### Flow 4: Forgot Password

```
POST /api/partners/auth/forgot-password
{ "email": "abc@example.com" }
      │
      ▼
┌─────────────────────────────────────┐
│ PartnerAuthService.forgot_password()│
│                                     │
│ 1. Get user by email + is_partner   │
│ 2. Get partner, check status ACTIVE │
│ 3. Generate reset token (UUID)      │
│ 4. Store in Redis (1h TTL)          │
│ 5. Send reset email                 │
└─────────────────────────────────────┘
      │
      ▼
POST /api/partners/auth/reset-password
{ "token": "uuid", "password": "...", "confirm_password": "..." }
      │
      ▼
┌─────────────────────────────────────┐
│ PartnerAuthService.reset_password() │
│                                     │
│ 1. Validate token from Redis        │
│ 2. Set new password on users_user   │
│ 3. Blacklist existing refresh tokens│
│ 4. Clear token from Redis           │
└─────────────────────────────────────┘
```

### Flow 5: Token Refresh

```
POST /api/partners/auth/refresh
{ "refresh_token": "..." }
      │
      ▼
┌─────────────────────────────────────┐
│ Standard JWT refresh with checks:   │
│ 1. Validate refresh token           │
│ 2. Get user, check is_partner       │
│ 3. Get partner, check status ACTIVE │
│ 4. Generate new access token        │
│ 5. Rotate refresh token             │
└─────────────────────────────────────┘
```

### Flow 6: Logout

```
POST /api/partners/auth/logout
Header: Authorization: Bearer {access_token}
{ "refresh_token": "..." }
      │
      ▼
Blacklist refresh token
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/partners/auth/set-password` | Token (URL) | Initial password setup |
| POST | `/api/partners/auth/login` | No | Partner login |
| POST | `/api/partners/auth/forgot-password` | No | Request reset email |
| POST | `/api/partners/auth/reset-password` | Token (URL) | Reset password |
| POST | `/api/partners/auth/refresh` | No | Refresh JWT |
| POST | `/api/partners/auth/logout` | JWT | Logout |
| GET | `/api/partners/auth/me` | JWT | Current partner profile |
| PUT | `/api/partners/auth/change-password` | JWT | Change password |

---

## Permission Classes

```python
# api/partners/common/permissions.py

from rest_framework.permissions import BasePermission

class IsPartner(BasePermission):
    """User is a partner (has partner_profile)"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'partner_profile')


class IsActivePartner(BasePermission):
    """Partner account is ACTIVE"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'partner_profile'):
            return False
        return request.user.partner_profile.status == 'ACTIVE'


class IsFranchise(IsActivePartner):
    """Partner is a Franchise"""
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.partner_profile.partner_type == 'FRANCHISE'


class IsRevenueVendor(IsActivePartner):
    """Partner is a Revenue Vendor (has dashboard access)"""
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        partner = request.user.partner_profile
        return (
            partner.partner_type == 'VENDOR' and
            partner.vendor_type == 'REVENUE'
        )


class IsVendor(IsActivePartner):
    """Partner is any Vendor type"""
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.partner_profile.partner_type == 'VENDOR'


class HasDashboardAccess(IsActivePartner):
    """Partner has dashboard access (Franchise OR Revenue Vendor)"""
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        partner = request.user.partner_profile
        if partner.partner_type == 'FRANCHISE':
            return True
        if partner.partner_type == 'VENDOR' and partner.vendor_type == 'REVENUE':
            return True
        return False
```

**Dashboard Access Rules (BR9):**
- `FRANCHISE` → Always has dashboard access
- `VENDOR` + `REVENUE` → Has dashboard access
- `VENDOR` + `NON_REVENUE` → NO dashboard access (login rejected)

---

## Serializers

```python
# api/partners/common/serializers/auth_serializers.py

from rest_framework import serializers

class PartnerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)


class SetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        self._validate_strength(data['password'])
        return data
    
    def _validate_strength(self, password):
        if not any(c.isupper() for c in password):
            raise serializers.ValidationError({"password": "Must contain uppercase"})
        if not any(c.islower() for c in password):
            raise serializers.ValidationError({"password": "Must contain lowercase"})
        if not any(c.isdigit() for c in password):
            raise serializers.ValidationError({"password": "Must contain digit"})


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class PartnerProfileSerializer(serializers.Serializer):
    """Response serializer for partner profile"""
    id = serializers.UUIDField()
    partner_type = serializers.CharField()
    vendor_type = serializers.CharField(allow_null=True)
    code = serializers.CharField()
    business_name = serializers.CharField()
    contact_phone = serializers.CharField()
    contact_email = serializers.CharField(allow_null=True)
    status = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    """Login/set-password response"""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    partner = PartnerProfileSerializer()
```

---

## Service Layer

```python
# api/partners/common/services/partner_auth_service.py

from api.common.services.base import BaseService
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
import uuid

class PartnerAuthService(BaseService):
    """Partner authentication service"""
    
    SETUP_TOKEN_TTL = 86400   # 24 hours
    RESET_TOKEN_TTL = 3600    # 1 hour
    
    def login(self, email: str, password: str) -> dict:
        """Authenticate partner and return JWT tokens"""
        from api.user.auth.models import User
        from api.partners.common.models import Partner
        
        # Get user
        user = User.objects.filter(
            email__iexact=email,
            is_partner=True,
            is_active=True
        ).first()
        
        if not user:
            raise self.exception("Invalid credentials", code="INVALID_CREDENTIALS")
        
        # Get partner
        partner = Partner.objects.filter(user=user).first()
        if not partner:
            raise self.exception("Partner profile not found", code="NO_PARTNER_PROFILE")
        
        # Check status
        if partner.status != 'ACTIVE':
            raise self.exception(
                f"Partner account is {partner.status.lower()}",
                code="PARTNER_NOT_ACTIVE"
            )
        
        # Check dashboard access (BR9)
        if partner.partner_type == 'VENDOR' and partner.vendor_type == 'NON_REVENUE':
            raise self.exception(
                "Non-revenue vendors do not have dashboard access",
                code="NO_DASHBOARD_ACCESS"
            )
        
        # Verify password
        if not user.check_password(password):
            raise self.exception("Invalid credentials", code="INVALID_CREDENTIALS")
        
        # Update last login
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "partner": self._serialize_partner(partner)
        }
    
    def set_initial_password(self, token: str, password: str) -> dict:
        """Set password from setup link"""
        # Validate token
        token_data = cache.get(f"partner:setup:{token}")
        if not token_data:
            raise self.exception("Invalid or expired token", code="INVALID_TOKEN")
        
        # Get partner
        from api.partners.common.models import Partner
        partner = Partner.objects.select_related('user').get(id=token_data['partner_id'])
        
        # Set password
        partner.user.set_password(password)
        partner.user.save()
        
        # Clear token
        cache.delete(f"partner:setup:{token}")
        
        # Generate JWT
        refresh = RefreshToken.for_user(partner.user)
        
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "partner": self._serialize_partner(partner)
        }
    
    def initiate_password_reset(self, email: str) -> dict:
        """Send password reset email"""
        from api.user.auth.models import User
        from api.partners.common.models import Partner
        
        user = User.objects.filter(email__iexact=email, is_partner=True).first()
        if not user:
            # Don't reveal if email exists
            return {"message": "If email exists, reset link will be sent"}
        
        partner = Partner.objects.filter(user=user, status='ACTIVE').first()
        if not partner:
            return {"message": "If email exists, reset link will be sent"}
        
        # Generate token
        token = str(uuid.uuid4())
        cache.set(
            f"partner:reset:{token}",
            {"partner_id": str(partner.id), "user_id": user.id, "email": email},
            timeout=self.RESET_TOKEN_TTL
        )
        
        # Send email via notify
        self._send_reset_email(partner, token)
        
        return {"message": "If email exists, reset link will be sent"}
    
    def complete_password_reset(self, token: str, password: str) -> dict:
        """Complete password reset"""
        token_data = cache.get(f"partner:reset:{token}")
        if not token_data:
            raise self.exception("Invalid or expired token", code="INVALID_TOKEN")
        
        from api.partners.common.models import Partner
        partner = Partner.objects.select_related('user').get(id=token_data['partner_id'])
        
        # Set new password
        partner.user.set_password(password)
        partner.user.save()
        
        # Clear token
        cache.delete(f"partner:reset:{token}")
        
        # Blacklist all existing tokens for this user
        # (handled by simplejwt if ROTATE_REFRESH_TOKENS is True)
        
        return {"message": "Password reset successful"}
    
    def change_password(self, user, current_password: str, new_password: str) -> dict:
        """Change password for logged-in partner"""
        if not user.check_password(current_password):
            raise self.exception("Current password is incorrect", code="WRONG_PASSWORD")
        
        user.set_password(new_password)
        user.save()
        
        return {"message": "Password changed successfully"}
    
    def refresh_token(self, refresh_token: str) -> dict:
        """Refresh JWT tokens with partner status check"""
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        
        try:
            old_refresh = RefreshToken(refresh_token)
            user_id = old_refresh['user_id']
        except TokenError:
            raise self.exception("Invalid refresh token", code="INVALID_TOKEN")
        
        # Check partner status
        from api.user.auth.models import User
        from api.partners.common.models import Partner
        
        user = User.objects.filter(id=user_id, is_partner=True, is_active=True).first()
        if not user:
            raise self.exception("User not found or inactive", code="USER_INACTIVE")
        
        partner = Partner.objects.filter(user=user, status='ACTIVE').first()
        if not partner:
            raise self.exception("Partner not active", code="PARTNER_NOT_ACTIVE")
        
        # Generate new tokens
        new_refresh = RefreshToken.for_user(user)
        
        # Blacklist old token
        old_refresh.blacklist()
        
        return {
            "access_token": str(new_refresh.access_token),
            "refresh_token": str(new_refresh)
        }
    
    def logout(self, refresh_token: str) -> dict:
        """Logout and blacklist token"""
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass  # Token already invalid/blacklisted
        
        return {"message": "Logged out successfully"}
    
    def get_current_partner(self, user) -> dict:
        """Get current partner profile"""
        from api.partners.common.models import Partner
        partner = Partner.objects.get(user=user)
        return self._serialize_partner(partner)
    
    def generate_setup_token(self, partner) -> str:
        """Generate password setup token for new partner"""
        token = str(uuid.uuid4())
        cache.set(
            f"partner:setup:{token}",
            {
                "partner_id": str(partner.id),
                "user_id": partner.user_id,
                "email": partner.contact_email or partner.user.email
            },
            timeout=self.SETUP_TOKEN_TTL
        )
        return token
    
    def _serialize_partner(self, partner) -> dict:
        return {
            "id": str(partner.id),
            "partner_type": partner.partner_type,
            "vendor_type": partner.vendor_type,
            "code": partner.code,
            "business_name": partner.business_name,
            "contact_phone": partner.contact_phone,
            "contact_email": partner.contact_email,
            "status": partner.status
        }
    
    def _send_setup_email(self, partner, token: str):
        """Send invitation email"""
        from api.user.notifications.services import notify
        from django.conf import settings
        
        setup_url = f"{settings.PARTNER_DASHBOARD_URL}/auth/setup/{token}"
        
        notify(
            user=partner.user,
            template_slug='partner_invitation',
            async_send=True,
            partner_name=partner.business_name,
            partner_type=partner.partner_type,
            partner_code=partner.code,
            setup_url=setup_url
        )
    
    def _send_reset_email(self, partner, token: str):
        """Send password reset email"""
        from api.user.notifications.services import notify
        from django.conf import settings
        
        reset_url = f"{settings.PARTNER_DASHBOARD_URL}/auth/reset/{token}"
        
        notify(
            user=partner.user,
            template_slug='partner_password_reset',
            async_send=True,
            partner_name=partner.business_name,
            reset_url=reset_url
        )
```

---

## Notification Templates

Add to `api/user/notifications/fixtures/templates.json`:

```json
[
  {
    "model": "notifications.notificationtemplate",
    "fields": {
      "name": "Partner Invitation",
      "slug": "partner_invitation",
      "notification_type": "partner_email",
      "title_template": "Welcome to ChargeGhar Partner Program",
      "message_template": "Hello {{ partner_name }}, your {{ partner_type }} account ({{ partner_code }}) has been created. Set your password: {{ setup_url }}",
      "is_active": true
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "fields": {
      "name": "Partner Password Reset",
      "slug": "partner_password_reset",
      "notification_type": "partner_email",
      "title_template": "Reset Your Partner Account Password",
      "message_template": "Hello {{ partner_name }}, reset your password: {{ reset_url }}. Expires in 1 hour.",
      "is_active": true
    }
  }
]
```

Add to `api/user/notifications/fixtures/rules.json`:

```json
[
  {
    "model": "notifications.notificationrule",
    "fields": {
      "notification_type": "partner_email",
      "send_in_app": false,
      "send_push": false,
      "send_sms": false,
      "send_email": true,
      "is_critical": true
    }
  }
]
```

---

## File Structure

```
api/partners/
├── __init__.py
├── common/
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py
│   ├── permissions.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── partner.py          # Django model for partners table
│   ├── serializers/
│   │   ├── __init__.py
│   │   └── auth_serializers.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── partner_auth_service.py
│   └── views/
│       ├── __init__.py
│       └── auth_views.py
├── franchise/
│   └── __init__.py
└── vendor/
    └── __init__.py
```

---

## Security

### Password Policy

| Rule | Requirement |
|------|-------------|
| Min Length | 8 characters |
| Max Length | 128 characters |
| Uppercase | At least 1 |
| Lowercase | At least 1 |
| Digit | At least 1 |

### Token Security

| Token | Storage | TTL | One-Time |
|-------|---------|-----|----------|
| Setup Token | Redis | 24h | Yes |
| Reset Token | Redis | 1h | Yes |
| JWT Access | Client | 30d | No |
| JWT Refresh | Client+Blacklist | 90d | Rotated |

---

## Implementation Order

1. Add `is_partner` field to `users_user` + migration
2. Create `partners` table (from schema.md)
3. Create `api/partners/common/` app structure
4. Add notification templates + rule
5. Implement `PartnerAuthService`
6. Implement serializers
7. Implement permission classes
8. Implement views
9. Configure URLs
10. Tests

---

## Cross-References

| Document | Purpose |
|----------|---------|
| `schema.md` | `partners` table definition |
| `Endpoints.md` | Full API endpoint list |
| `schema_mapping.md` | Field lifecycle |
| `Business Rules.md` | BR9: Dashboard access rules |
