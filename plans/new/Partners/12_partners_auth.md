```markdown
# Feature: Partner Authentication System

**App**: `api/partners/common/`  
**Priority**: Phase 1 (Pre-requisite for Partner Dashboard)  
**Date**: 2026-01-13

---

## Overview

Authentication system for Partner Dashboard (Franchise & Vendor). Unlike the user app (OTP-based), partners will use **password-based authentication** (same approach as admin). Admin creates partner accounts and sends credentials via email.

---

## Current System Analysis

### User Auth (OTP-based) - `api/user/auth/`

| Component | Implementation |
|-----------|----------------|
| **Flow** | 3-step: Request OTP → Verify OTP → Complete Auth |
| **Password** | Disabled for regular users (enabled only for `is_staff`/`is_superuser`) |
| **OTP Storage** | Redis cache via `OTPHandler` (5 min expiry) |
| **Verification** | UUID token via `VerificationTokenHandler` (10 min expiry) |
| **JWT** | `rest_framework_simplejwt` with blacklist support |
| **Token Lifetime** | Access: 30 days, Refresh: 90 days (configurable) |

### Admin Auth (Password-based) - `api/admin/`

| Component | Implementation |
|-----------|----------------|
| **Flow** | Direct login: Email + Password → JWT tokens |
| **Endpoint** | `POST /api/admin/login` |
| **Permission** | Requires `is_staff=True` on `User` model |
| **Profile Model** | `AdminProfile` with roles (super_admin, admin, moderator) |
| **Service** | `AdminProfileService.authenticate_admin()` |

### Existing Infrastructure

| Component | Location | Description |
|-----------|----------|-------------|
| `BaseService` | `api/common/services/base.py` | Logging, error handling |
| `CRUDService` | `api/common/services/base.py` | CRUD operations |
| `ServiceException` | `api/common/services/base.py` | Custom exception with context |
| `BaseAPIView` | `api/common/mixins/` | StandardResponse, ServiceHandler, Cache, Pagination, Filter |
| `CustomViewRouter` | `api/common/routers.py` | Route registration decorator |
| `notify` | `api/user/notifications/services/notify.py` | Universal notification (template + rules based) |
| `EmailService` | `api/user/notifications/services/email.py` | HTML email via templates (used by notify internally) |
| `NotificationTemplate` | `api/user/notifications/models/template.py` | Template model with `slug`, `title_template`, `message_template` |
| `NotificationRule` | `api/user/notifications/models/rule.py` | Channel rules (`send_email`, `send_sms`, `send_push`, `send_in_app`) |
| `BaseModel` | `api/common/models/base.py` | UUID pk, created_at, updated_at |
| JWT Config | `api/config/jwt.py` | SIMPLE_JWT settings |
| Token Blacklist | `rest_framework_simplejwt.token_blacklist` | Already in INSTALLED_APPS |

### User Model Constraints - `api/user/auth/models/user.py`

```python
def set_password(self, raw_password):
    """Allow password setting for admin users, disable for regular users"""
    if self.is_staff or self.is_superuser:
        super().set_password(raw_password)
    else:
        pass  # Disabled for OTP-only users

def check_password(self, raw_password):
    if self.is_staff or self.is_superuser:
        return super().check_password(raw_password)
    else:
        return False
```

**Key Decision**: Partners will have `is_partner=True` flag to enable password functionality. The `User` model's `set_password` and `check_password` methods need modification to support partners.

---

## Authentication Flow

### Flow 1: Partner Account Creation (Admin-initiated)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     PARTNER ACCOUNT CREATION                            │
└─────────────────────────────────────────────────────────────────────────┘

[Admin Dashboard]
       │
       ▼
POST /api/admin/partners/create
{
  "partner_type": "FRANCHISE" | "VENDOR",
  "name": "ABC Franchise",
  "contact_email": "abc@example.com",
  "contact_phone": "+977-9800000000",
  "address": "Kathmandu, Nepal",
  ... (partner-specific data)
}
       │
       ▼
┌──────────────────────────────────────┐
│ AdminPartnerService.create_partner() │
│                                      │
│ 1. Validate email not exists         │
│ 2. Create User (is_partner=True)     │
│ 3. Create Partner base model         │
│ 4. Create Franchise/Vendor model     │
│ 5. Generate password_setup_token     │
│ 6. Store token in Redis (24h expiry) │
│ 7. Send invitation email             │
└──────────────────────────────────────┘
       │
       ▼
[Email sent to partner]
"Welcome to ChargeGhar Partner Program!
Click here to set your password: 
https://partners.chargeghar.com/auth/setup/{token}"
```

### Flow 2: Partner Initial Password Setup

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     INITIAL PASSWORD SETUP                              │
└─────────────────────────────────────────────────────────────────────────┘

[Partner clicks email link]
       │
       ▼
GET /partners/auth/setup/{token} (Frontend)
       │
       ▼
POST /api/partners/auth/set-password
{
  "token": "uuid-password-setup-token",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
       │
       ▼
┌──────────────────────────────────────────┐
│ PartnerAuthService.set_initial_password()│
│                                          │
│ 1. Validate token from Redis             │
│ 2. Check token not expired (24h)         │
│ 3. Get partner from token data           │
│ 4. Validate password strength            │
│ 5. Set password on User model            │
│ 6. Update Partner.password_set_at        │
│ 7. Clear token from Redis                │
│ 8. Generate JWT tokens                   │
│ 9. Log action                            │
└──────────────────────────────────────────┘
       │
       ▼
Response:
{
  "success": true,
  "message": "Password set successfully",
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "user": {...},
    "partner": {...}
  }
}
```

### Flow 3: Partner Login

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PARTNER LOGIN                                 │
└─────────────────────────────────────────────────────────────────────────┘

POST /api/partners/auth/login
{
  "email": "abc@example.com",
  "password": "SecurePass123!"
}
       │
       ▼
┌──────────────────────────────────────────┐
│ PartnerAuthService.authenticate_partner()│
│                                          │
│ 1. Get User by email + is_partner=True   │
│ 2. Check User.is_active                  │
│ 3. Check Partner.status == 'ACTIVE'      │
│ 4. Check password_set_at is not null     │
│ 5. Verify password                       │
│ 6. Update last_login                     │
│ 7. Generate JWT tokens                   │
│ 8. Log action                            │
└──────────────────────────────────────────┘
       │
       ▼
Response:
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "user": {
      "id": "uuid",
      "email": "abc@example.com",
      "username": "abc_franchise"
    },
    "partner": {
      "id": "uuid",
      "partner_type": "FRANCHISE",
      "code": "FR-001",
      "name": "ABC Franchise",
      "status": "ACTIVE"
    }
  }
}
```

### Flow 4: Forgot Password

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FORGOT PASSWORD                                 │
└─────────────────────────────────────────────────────────────────────────┘

POST /api/partners/auth/forgot-password
{
  "email": "abc@example.com"
}
       │
       ▼
┌────────────────────────────────────────────┐
│ PartnerAuthService.initiate_password_reset()│
│                                            │
│ 1. Get User by email + is_partner=True     │
│ 2. Check Partner.status == 'ACTIVE'        │
│ 3. Generate password_reset_token (UUID)    │
│ 4. Store in Redis (1h expiry)              │
│ 5. Send password reset email               │
└────────────────────────────────────────────┘
       │
       ▼
[Email sent to partner]
"Reset your password:
https://partners.chargeghar.com/auth/reset/{token}"

POST /api/partners/auth/reset-password
{
  "token": "uuid-reset-token",
  "password": "NewSecurePass456!",
  "confirm_password": "NewSecurePass456!"
}
       │
       ▼
┌──────────────────────────────────────────────┐
│ PartnerAuthService.complete_password_reset() │
│                                              │
│ 1. Validate token from Redis                 │
│ 2. Get partner from token data               │
│ 3. Validate password strength                │
│ 4. Set new password                          │
│ 5. Blacklist all existing refresh tokens     │
│ 6. Clear token from Redis                    │
│ 7. Log action                                │
└──────────────────────────────────────────────┘
```

### Flow 5: Token Refresh

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          TOKEN REFRESH                                  │
└─────────────────────────────────────────────────────────────────────────┘

POST /api/partners/auth/refresh
{
  "refresh_token": "existing-refresh-token"
}
       │
       ▼
┌──────────────────────────────────────────┐
│ PartnerAuthService.refresh_token()       │
│                                          │
│ 1. Validate refresh token                │
│ 2. Get user from token payload           │
│ 3. Check User.is_active + Partner.status │
│ 4. Generate new access token             │
│ 5. Rotate refresh token (per JWT config) │
│ 6. Blacklist old refresh token           │
│ 7. Log action                            │
└──────────────────────────────────────────┘
       │
       ▼
Response:
{
  "success": true,
  "data": {
    "access_token": "new-access-token",
    "refresh_token": "new-refresh-token"
  }
}
```

### Flow 6: Logout

```
┌─────────────────────────────────────────────────────────────────────────┐
│                             LOGOUT                                      │
└─────────────────────────────────────────────────────────────────────────┘

POST /api/partners/auth/logout
Header: Authorization: Bearer {access_token}
{
  "refresh_token": "current-refresh-token"
}
       │
       ▼
┌──────────────────────────────────────────┐
│ PartnerAuthService.logout()              │
│                                          │
│ 1. Validate refresh token belongs to user│
│ 2. Blacklist refresh token               │
│ 3. Log action                            │
└──────────────────────────────────────────┘
       │
       ▼
Response:
{
  "success": true,
  "message": "Logout successful",
  "data": {
    "logged_out_at": "2026-01-13T10:30:00Z"
  }
}
```

---

## Database Schema Updates

### Update 1: User Model Modification

**File**: `api/user/auth/models/user.py`

Add new field and modify password methods:

```python
class User(AbstractBaseUser, PermissionsMixin):
    # ... existing fields ...
    
    # NEW: Partner flag (enables password for partners)
    is_partner = models.BooleanField(default=False)
    
    def set_password(self, raw_password):
        """Allow password for admin AND partner users"""
        if self.is_staff or self.is_superuser or self.is_partner:
            super().set_password(raw_password)
        else:
            pass  # Disabled for OTP-only users
    
    def check_password(self, raw_password):
        """Allow password check for admin AND partner users"""
        if self.is_staff or self.is_superuser or self.is_partner:
            return super().check_password(raw_password)
        else:
            return False
```

**Migration Required**: Yes - Add `is_partner` BooleanField

---

### Update 2: Partner Model Extension

**File**: `api/partners/common/models/partner.py`

Extend the Partner model from `02_partner_models.md` with auth fields:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `password_set_at` | DateTimeField | When password was set | NULL (not set yet) |
| `password_reset_at` | DateTimeField | Last password reset | NULL |
| `last_login_at` | DateTimeField | Last login timestamp | NULL |
| `login_count` | IntegerField | Total login count | default=0 |
| `failed_login_attempts` | IntegerField | Failed attempts (reset on success) | default=0 |
| `locked_until` | DateTimeField | Account lock timestamp | NULL |

**Partner Status Choices** (from `02_partner_models.md`):
```python
STATUS_CHOICES = [
    ('PENDING_SETUP', 'Pending Setup'),  # NEW: Awaiting password setup
    ('ACTIVE', 'Active'),
    ('INACTIVE', 'Inactive'),
    ('SUSPENDED', 'Suspended'),
]
```

---

### Schema: Password Setup Token (Redis)

```
Key: partner_password_setup:{token}
Value: {
    "partner_id": "uuid",
    "user_id": "uuid", 
    "email": "abc@example.com",
    "created_at": "2026-01-13T10:00:00Z",
    "purpose": "INITIAL_SETUP"
}
TTL: 86400 seconds (24 hours)
```

### Schema: Password Reset Token (Redis)

```
Key: partner_password_reset:{token}
Value: {
    "partner_id": "uuid",
    "user_id": "uuid",
    "email": "abc@example.com",
    "created_at": "2026-01-13T10:00:00Z",
    "purpose": "PASSWORD_RESET"
}
TTL: 3600 seconds (1 hour)
```

---

## API Endpoints

### Partner Auth Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/api/partners/auth/set-password` | Token (URL) | Set initial password |
| POST | `/api/partners/auth/login` | No | Partner login |
| POST | `/api/partners/auth/forgot-password` | No | Request password reset |
| POST | `/api/partners/auth/reset-password` | Token (URL) | Reset password |
| POST | `/api/partners/auth/refresh` | No | Refresh JWT token |
| POST | `/api/partners/auth/logout` | JWT | Logout and blacklist token |
| GET | `/api/partners/auth/me` | JWT | Get current partner profile |
| PUT | `/api/partners/auth/change-password` | JWT | Change password (logged in) |

### Admin Partner Management Endpoints

| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| POST | `/api/admin/partners/create` | IsSuperAdmin | Create partner account |
| POST | `/api/admin/partners/{id}/resend-invite` | IsStaffPermission | Resend invitation email |
| POST | `/api/admin/partners/{id}/reset-password` | IsSuperAdmin | Force password reset |
| PUT | `/api/admin/partners/{id}/status` | IsStaffPermission | Activate/Deactivate partner |

---

## Serializers

### Partner Login Serializer

```python
# api/partners/common/serializers/auth_serializers.py

class PartnerLoginSerializer(serializers.Serializer):
    """Serializer for partner login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)


class SetPasswordSerializer(serializers.Serializer):
    """Serializer for initial password setup"""
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    confirm_password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        self._validate_password_strength(data['password'])
        return data
    
    def _validate_password_strength(self, password):
        """Enforce password policy"""
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters"})
        if not any(c.isupper() for c in password):
            raise serializers.ValidationError({"password": "Password must contain uppercase letter"})
        if not any(c.islower() for c in password):
            raise serializers.ValidationError({"password": "Password must contain lowercase letter"})
        if not any(c.isdigit() for c in password):
            raise serializers.ValidationError({"password": "Password must contain a digit"})


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request"""
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset"""
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    confirm_password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password while logged in"""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    confirm_password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for token refresh"""
    refresh_token = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout"""
    refresh_token = serializers.CharField(help_text="JWT refresh token to blacklist")


class PartnerAuthResponseSerializer(serializers.Serializer):
    """Response serializer for partner auth"""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = serializers.DictField()
    partner = serializers.DictField()
```

---

## Permission Classes

### New Permissions

```python
# api/partners/common/permissions.py

from rest_framework.permissions import BasePermission


class IsPartner(BasePermission):
    """Permission to check if user is a partner"""
    message = "Partner access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_partner and hasattr(request.user, 'partner')


class IsActivePartner(BasePermission):
    """Permission to check if partner account is active"""
    message = "Active partner account required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not request.user.is_partner:
            return False
        try:
            return request.user.partner.status == 'ACTIVE'
        except AttributeError:
            return False


class IsFranchise(IsActivePartner):
    """Permission for franchise partners only"""
    message = "Franchise access required"
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.partner.partner_type == 'FRANCHISE'


class IsVendor(IsActivePartner):
    """Permission for vendor partners only"""
    message = "Vendor access required"
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.partner.partner_type == 'VENDOR'


class IsRevenueVendor(IsVendor):
    """Permission for revenue vendors only (have dashboard access)"""
    message = "Revenue vendor access required"
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        try:
            return request.user.partner.vendor.vendor_type == 'REVENUE'
        except AttributeError:
            return False
```

---

## Service Layer

### PartnerAuthService

```python
# api/partners/common/services/partner_auth_service.py

class PartnerAuthService(BaseService):
    """Service for partner authentication operations"""
    
    PASSWORD_SETUP_TOKEN_EXPIRY = 86400  # 24 hours
    PASSWORD_RESET_TOKEN_EXPIRY = 3600   # 1 hour
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes
    
    def __init__(self):
        super().__init__()
        from api.partners.common.repositories import PartnerRepository
        self.partner_repo = PartnerRepository()
    
    # --- Authentication Methods ---
    
    def authenticate_partner(self, email: str, password: str, request=None) -> dict:
        """Authenticate partner and return JWT tokens"""
        ...
    
    def set_initial_password(self, token: str, password: str, request=None) -> dict:
        """Set initial password from invitation link"""
        ...
    
    def initiate_password_reset(self, email: str, request=None) -> dict:
        """Send password reset email"""
        ...
    
    def complete_password_reset(self, token: str, password: str, request=None) -> dict:
        """Complete password reset"""
        ...
    
    def change_password(self, user, current_password: str, new_password: str, request=None) -> dict:
        """Change password for logged-in partner"""
        ...
    
    def refresh_token(self, refresh_token: str, request=None) -> dict:
        """Refresh JWT tokens"""
        ...
    
    def logout(self, user, refresh_token: str, request=None) -> dict:
        """Logout and blacklist token"""
        ...
    
    def get_current_partner(self, user) -> dict:
        """Get current partner profile"""
        ...
    
    # --- Token Management ---
    
    def _generate_setup_token(self, partner) -> str:
        """Generate password setup token"""
        ...
    
    def _validate_setup_token(self, token: str) -> dict:
        """Validate password setup token"""
        ...
    
    def _generate_reset_token(self, partner) -> str:
        """Generate password reset token"""
        ...
    
    def _validate_reset_token(self, token: str) -> dict:
        """Validate password reset token"""
        ...
    
    # --- Security ---
    
    def _check_account_lock(self, partner):
        """Check if account is locked due to failed attempts"""
        ...
    
    def _record_failed_attempt(self, partner):
        """Record failed login attempt"""
        ...
    
    def _reset_failed_attempts(self, partner):
        """Reset failed attempts on successful login"""
        ...
    
    # --- Notification ---
    
    def _send_invitation_email(self, partner, setup_token: str):
        """Send partner invitation email using notify system"""
        from api.user.notifications.services import notify
        
        setup_url = f"{settings.PARTNER_DASHBOARD_URL}/auth/setup/{setup_token}"
        
        # Uses 'partner_invitation' template + 'partner_email' rule
        notify(
            user=partner.user,
            template_slug='partner_invitation',
            async_send=True,
            partner_name=partner.name,
            partner_type=partner.get_partner_type_display(),
            partner_code=partner.code,
            setup_url=setup_url
        )
    
    def _send_password_reset_email(self, partner, reset_token: str):
        """Send password reset email using notify system"""
        from api.user.notifications.services import notify
        
        reset_url = f"{settings.PARTNER_DASHBOARD_URL}/auth/reset/{reset_token}"
        
        # Uses 'partner_password_reset' template + 'partner_email' rule
        notify(
            user=partner.user,
            template_slug='partner_password_reset',
            async_send=True,
            partner_name=partner.name,
            reset_url=reset_url
        )
```

---

## Notification System Integration

Partner auth uses the existing `notify` system with templates and rules. This ensures consistency with the rest of the application.

### New Notification Templates (Fixtures)

**File**: `api/user/notifications/fixtures/templates.json` (append)

```json
[
  {
    "model": "notifications.notificationtemplate",
    "pk": 50,
    "fields": {
      "name": "Partner Invitation",
      "slug": "partner_invitation",
      "notification_type": "partner_email",
      "title_template": "Welcome to ChargeGhar Partner Program",
      "message_template": "Hello {{ partner_name }}, your {{ partner_type }} account ({{ partner_code }}) has been created. Set your password here: {{ setup_url }}",
      "is_active": true,
      "created_at": "2026-01-13T10:00:00Z",
      "updated_at": "2026-01-13T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 51,
    "fields": {
      "name": "Partner Password Reset",
      "slug": "partner_password_reset",
      "notification_type": "partner_email",
      "title_template": "Reset Your Partner Account Password",
      "message_template": "Hello {{ partner_name }}, click here to reset your password: {{ reset_url }}. This link expires in 1 hour.",
      "is_active": true,
      "created_at": "2026-01-13T10:00:00Z",
      "updated_at": "2026-01-13T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 52,
    "fields": {
      "name": "Partner Password Changed",
      "slug": "partner_password_changed",
      "notification_type": "partner_email",
      "title_template": "Password Changed Successfully",
      "message_template": "Hello {{ partner_name }}, your password was changed on {{ changed_at }}. If you did not make this change, contact support immediately.",
      "is_active": true,
      "created_at": "2026-01-13T10:00:00Z",
      "updated_at": "2026-01-13T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 53,
    "fields": {
      "name": "Partner Account Suspended",
      "slug": "partner_account_suspended",
      "notification_type": "partner_email",
      "title_template": "Partner Account Suspended",
      "message_template": "Hello {{ partner_name }}, your partner account has been suspended. Reason: {{ reason }}. Contact support for assistance.",
      "is_active": true,
      "created_at": "2026-01-13T10:00:00Z",
      "updated_at": "2026-01-13T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 54,
    "fields": {
      "name": "Partner Account Reactivated",
      "slug": "partner_account_reactivated",
      "notification_type": "partner_email",
      "title_template": "Partner Account Reactivated",
      "message_template": "Hello {{ partner_name }}, your partner account has been reactivated. You can now log in to your dashboard.",
      "is_active": true,
      "created_at": "2026-01-13T10:00:00Z",
      "updated_at": "2026-01-13T10:00:00Z"
    }
  }
]
```

### New Notification Rule (Fixtures)

**File**: `api/user/notifications/fixtures/rules.json` (append)

```json
[
  {
    "model": "notifications.notificationrule",
    "pk": 20,
    "fields": {
      "notification_type": "partner_email",
      "send_in_app": false,
      "send_push": false,
      "send_sms": false,
      "send_email": true,
      "is_critical": true,
      "created_at": "2026-01-13T10:00:00Z",
      "updated_at": "2026-01-13T10:00:00Z"
    }
  }
]
```

**Rule Explanation**:
- `send_in_app: false` - Partners don't use the user app
- `send_push: false` - Partners don't have FCM tokens
- `send_sms: false` - Email is primary for B2B
- `send_email: true` - All partner notifications go via email
- `is_critical: true` - Auth emails must be sent immediately

### Email HTML Templates

**File**: `api/user/notifications/templates/partner_invitation.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to ChargeGhar Partner Program</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        .header {
            background-color: #FF5722;
            color: #ffffff;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
        }
        .content {
            padding: 40px;
        }
        .partner-info {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .button {
            display: inline-block;
            background-color: #FF5722;
            color: #ffffff;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            margin: 20px 0;
        }
        .note {
            font-size: 14px;
            color: #777;
            margin-top: 20px;
        }
        .footer {
            background-color: #f9f9f9;
            color: #777;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            border-top: 1px solid #eee;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to ChargeGhar!</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{{ partner_name }}</strong>,</p>
            <p>Congratulations! Your <strong>{{ partner_type }}</strong> partner account has been created.</p>
            
            <div class="partner-info">
                <p><strong>Partner Code:</strong> {{ partner_code }}</p>
                <p><strong>Account Type:</strong> {{ partner_type }}</p>
            </div>
            
            <p>To access your Partner Dashboard, you need to set up your password:</p>
            
            <a href="{{ setup_url }}" class="button">Set Your Password</a>
            
            <p class="note">
                ⏰ This link will expire in <strong>24 hours</strong>.<br>
                🔒 Keep your credentials secure and do not share them.
            </p>
        </div>
        <div class="footer">
            <p>&copy; 2026 ChargeGhar Nepal. All rights reserved.</p>
            <p>If you did not expect this email, please contact support.</p>
        </div>
    </div>
</body>
</html>
```

**File**: `api/user/notifications/templates/partner_password_reset.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        .header {
            background-color: #FF5722;
            color: #ffffff;
            padding: 30px;
            text-align: center;
        }
        .content {
            padding: 40px;
        }
        .button {
            display: inline-block;
            background-color: #FF5722;
            color: #ffffff;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            margin: 20px 0;
        }
        .note {
            font-size: 14px;
            color: #777;
            margin-top: 20px;
        }
        .warning {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .footer {
            background-color: #f9f9f9;
            color: #777;
            padding: 20px;
            text-align: center;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{{ partner_name }}</strong>,</p>
            <p>We received a request to reset your password for your ChargeGhar Partner account.</p>
            
            <p>Click the button below to reset your password:</p>
            
            <a href="{{ reset_url }}" class="button">Reset Password</a>
            
            <p class="note">
                ⏰ This link will expire in <strong>1 hour</strong>.
            </p>
            
            <div class="warning">
                ⚠️ <strong>Didn't request this?</strong><br>
                If you did not request a password reset, please ignore this email. Your password will remain unchanged.
            </div>
        </div>
        <div class="footer">
            <p>&copy; 2026 ChargeGhar Nepal. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
```

---

## File Structure

```
api/partners/
├── __init__.py
├── common/
│   ├── __init__.py
│   ├── apps.py                          # NEW: Django AppConfig
│   ├── urls.py                          # NEW: URL patterns
│   ├── permissions.py                   # NEW: IsPartner, IsFranchise, IsVendor
│   ├── models/
│   │   ├── __init__.py
│   │   └── partner.py                   # From 02_partner_models.md + auth fields
│   ├── serializers/
│   │   ├── __init__.py
│   │   └── auth_serializers.py          # NEW: Login, SetPassword, etc.
│   ├── services/
│   │   ├── __init__.py
│   │   └── partner_auth_service.py      # NEW: Authentication service
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── partner_repository.py        # NEW: Partner data access
│   ├── views/
│   │   ├── __init__.py
│   │   └── partner_auth_views.py        # NEW: Auth endpoints
│   └── utils/
│       ├── __init__.py
│       └── password_token_handler.py    # NEW: Token generation/validation
├── franchise/
│   └── __init__.py                      # (Franchise-specific later)
└── vendor/
    └── __init__.py                      # (Vendor-specific later)
```

---

## AppConfig Registration

### Add to INSTALLED_APPS

**File**: `api/config/application.py`

```python
INSTALLED_APPS = [
    # ... existing apps ...
    
    # Partner Apps
    "api.partners.common.apps.PartnersCommonConfig",
]
```

### Partner Common App Config

**File**: `api/partners/common/apps.py`

```python
from django.apps import AppConfig


class PartnersCommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.partners.common'
    label = 'partners_common'
    verbose_name = 'Partners - Common'
```

---

## URL Configuration

### Partner Auth URLs

**File**: `api/partners/common/urls.py`

```python
from api.partners.common.views import partner_auth_router

urlpatterns = [
    *partner_auth_router.urls,
]
```

### Main URL Include

**File**: `api/urls.py` (or main urls file)

```python
urlpatterns = [
    # ... existing patterns ...
    path('api/', include('api.partners.common.urls')),
]
```

---

## Security Considerations

### Password Policy

| Rule | Requirement |
|------|-------------|
| Minimum Length | 8 characters |
| Maximum Length | 128 characters |
| Uppercase | At least 1 uppercase letter |
| Lowercase | At least 1 lowercase letter |
| Digit | At least 1 digit |
| Special Character | Optional (recommended) |

### Rate Limiting

| Action | Limit |
|--------|-------|
| Login Attempts | 5 attempts, then 15-min lockout |
| Password Reset Request | 3 requests per hour per email |
| Token Refresh | No limit (tokens self-expire) |

### Token Security

| Token Type | Storage | Expiry | One-Time Use |
|------------|---------|--------|--------------|
| Password Setup Token | Redis | 24 hours | Yes |
| Password Reset Token | Redis | 1 hour | Yes |
| JWT Access Token | Client | 30 days | No (until expired) |
| JWT Refresh Token | Client + Blacklist | 90 days | Rotated |

---

## Migration Plan

### Step 1: User Model Migration

```python
# api/user/auth/migrations/000X_add_is_partner.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0008_...'),  # Latest auth migration
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_partner',
            field=models.BooleanField(default=False),
        ),
    ]
```

### Step 2: Partner Model Migration (after 02_partner_models.md)

Ensure the Partner model includes auth fields:
- `password_set_at`
- `password_reset_at`
- `last_login_at`
- `login_count`
- `failed_login_attempts`
- `locked_until`

---

## Testing Requirements

### Unit Tests

| Test Case | Description |
|-----------|-------------|
| `test_partner_login_success` | Valid credentials return tokens |
| `test_partner_login_wrong_password` | Invalid password returns 401 |
| `test_partner_login_inactive_account` | Inactive partner returns 403 |
| `test_partner_login_lockout` | 5 failed attempts triggers lockout |
| `test_set_initial_password_valid_token` | Valid token sets password |
| `test_set_initial_password_expired_token` | Expired token returns 400 |
| `test_forgot_password_sends_email` | Valid email sends reset link |
| `test_reset_password_valid_token` | Valid token resets password |
| `test_refresh_token_valid` | Valid refresh returns new tokens |
| `test_logout_blacklists_token` | Logout blacklists refresh token |

### Integration Tests

| Test Case | Description |
|-----------|-------------|
| `test_full_partner_setup_flow` | Admin create → Email → Set password → Login |
| `test_password_reset_flow` | Forgot → Email → Reset → Login with new password |
| `test_token_rotation` | Multiple refresh calls rotate tokens |

---

## Dependencies

### Existing Dependencies (Already Installed)

| Package | Version | Purpose |
|---------|---------|---------|
| `djangorestframework-simplejwt` | >= 5.0 | JWT authentication |
| `django-redis` | - | Token storage in Redis |

### No New Dependencies Required

All functionality can be built using existing packages.

---

## Cross-References

| Related Document | Purpose |
|------------------|---------|
| `02_partner_models.md` | Base Partner, Franchise, Vendor models |
| `api/user/auth/` | Reference implementation for OTP auth |
| `api/admin/views/auth_views.py` | Reference for password-based auth |
| `api/admin/services/admin_profile_service.py` | Reference for admin authentication service |
| `api/common/services/base.py` | BaseService, ServiceException |
| `api/common/routers.py` | CustomViewRouter for endpoint registration |
| `api/user/notifications/services/notify.py` | `notify()` function for sending notifications |
| `api/user/notifications/models/template.py` | NotificationTemplate model |
| `api/user/notifications/models/rule.py` | NotificationRule model (channel routing) |
| `api/user/notifications/fixtures/templates.json` | Existing notification templates |
| `api/user/notifications/fixtures/rules.json` | Existing notification rules |

---

## Implementation Order

1. **User Model Update**: Add `is_partner` field + migration
2. **Partner Model Update**: Add auth fields to Partner model
3. **Partner Common App**: Create apps.py, register in INSTALLED_APPS
4. **Notification Fixtures**: Add partner templates + rule to fixtures
5. **Email HTML Templates**: Create partner_invitation.html, partner_password_reset.html
6. **Utils**: Create `password_token_handler.py`
7. **Repository**: Create `partner_repository.py`
8. **Service**: Create `partner_auth_service.py`
9. **Serializers**: Create `auth_serializers.py`
10. **Permissions**: Create `permissions.py`
11. **Views**: Create `partner_auth_views.py`
12. **URLs**: Create `urls.py`, include in main urls
13. **Admin Endpoints**: Add partner management endpoints to admin app
14. **Tests**: Unit and integration tests
15. **Documentation**: API documentation
```
