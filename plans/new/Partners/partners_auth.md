# Partner Authentication System

> **Version:** 3.0  
> **Last Updated:** 2026-01-24  
> **Status:** Simplified - Removed over-engineered password flows

---

## Overview

Password-based authentication for Partner Dashboard (Franchise & Revenue Vendor). Unlike user app (OTP-based), partners use password authentication similar to admin.

**Key Principle:** Partners are existing `users_user` records linked to `partners` table via `user_id`.

**Simplified Approach:** Initial password is set by admin during partner creation. Partners can only change their password when logged in - no self-service password reset flow.

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
# Password Setup Token (24h) - Used during admin-initiated partner creation
Key: partner:setup:{token}
Value: {"partner_id": "uuid", "user_id": 123, "email": "x@y.com"}
TTL: 86400
```

---

## Authentication Flows

### Flow 1: Partner Account Creation (Admin-Initiated)

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
│ 5. Set initial password (admin)     │
│ 6. Generate setup token (optional)  │
│ 7. Send invitation email with creds │
└─────────────────────────────────────┘
      │
      ▼
Email: "Your partner account credentials: email + password"
```

### Flow 2: Partner Login

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

### Flow 3: Change Password (Authenticated)

```
PUT /api/partners/auth/change-password
Header: Authorization: Bearer {access_token}
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!",
  "confirm_password": "NewPass456!"
}
      │
      ▼
┌─────────────────────────────────────┐
│ PartnerPasswordService              │
│   .change_password()                │
│                                     │
│ 1. Verify current password          │
│ 2. Validate new password != current │
│ 3. Set new password on users_user   │
└─────────────────────────────────────┘
      │
      ▼
Response: { "message": "Password changed successfully" }
```

### Flow 4: Token Refresh

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

### Flow 5: Logout

```
POST /api/partners/auth/logout
Header: Authorization: Bearer {access_token}
{ "refresh_token": "..." }
      │
      ▼
Blacklist refresh token
```

### Flow 6: Password Recovery (Admin-Assisted)

If a partner forgets their password, they must contact admin/support:

```
Partner contacts Admin
      │
      ▼
Admin Dashboard: Reset partner password
      │
      ▼
Admin sets new password for partner
      │
      ▼
Admin communicates new password to partner
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/partners/auth/login` | No | Partner login |
| POST | `/api/partners/auth/refresh` | No | Refresh JWT |
| POST | `/api/partners/auth/logout` | JWT | Logout |
| GET | `/api/partners/auth/me` | JWT | Current partner profile |
| PUT | `/api/partners/auth/change-password` | JWT | Change password (authenticated) |

**Removed Endpoints:**
- ~~POST `/api/partners/auth/set-password`~~ - Initial password set by admin
- ~~POST `/api/partners/auth/forgot-password`~~ - Contact admin for reset
- ~~POST `/api/partners/auth/reset-password`~~ - Admin handles resets

---

## Permission Classes

```python
# api/partners/auth/permissions.py

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
# api/partners/auth/serializers/password_serializers.py

from rest_framework import serializers

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (authenticated)."""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError({"new_password": "New password must be different"})
        return data
```

---

## Service Layer

```python
# api/partners/auth/services/password_service.py

from api.common.services.base import BaseService, ServiceException
from api.partners.common.repositories import PartnerRepository

class PartnerPasswordService(BaseService):
    """Service for partner password operations."""
    
    def change_password(self, user, current_password: str, new_password: str) -> dict:
        """Change password for logged-in partner."""
        if not user.check_password(current_password):
            raise ServiceException(
                detail="Current password is incorrect",
                code="WRONG_PASSWORD"
            )
        
        user.set_password(new_password)
        user.save()
        
        partner = PartnerRepository.get_by_user_id(user.id)
        self.log_info(f"Password changed for partner: {partner.code if partner else user.id}")
        
        return {"message": "Password changed successfully"}
```

---

## File Structure

```
api/partners/auth/
├── __init__.py
├── apps.py
├── permissions.py
├── urls.py
├── repositories/
│   └── __init__.py
├── serializers/
│   ├── __init__.py
│   ├── login_serializers.py
│   ├── password_serializers.py      # Only ChangePasswordSerializer
│   ├── response_serializers.py
│   └── token_serializers.py
├── services/
│   ├── __init__.py
│   ├── auth_service.py              # Login, profile, token delegation
│   ├── password_service.py          # Only change_password
│   └── token_service.py             # JWT + setup token (for admin use)
└── views/
    ├── __init__.py
    ├── login_view.py
    ├── password_views.py            # Only PartnerChangePasswordView
    ├── profile_view.py
    └── token_views.py
```

---

## Security

### Password Policy

| Rule | Requirement |
|------|-------------|
| Min Length | 8 characters |
| Max Length | 128 characters |

### Token Security

| Token | Storage | TTL | One-Time |
|-------|---------|-----|----------|
| Setup Token | Redis | 24h | Yes (admin use) |
| JWT Access | Client | 30d | No |
| JWT Refresh | Client+Blacklist | 90d | Rotated |

---

## Rationale for Simplification

The following endpoints were removed as over-engineered:

1. **`set-password`** - Admin sets initial password during partner creation
2. **`forgot-password`** - Partners contact admin for password issues
3. **`reset-password`** - Admin handles all password resets

**Benefits:**
- Simpler codebase with fewer attack vectors
- Admin maintains control over partner credentials
- Reduced email infrastructure requirements
- Partners have a clear support path for password issues

---

## Cross-References

| Document | Purpose |
|----------|---------|
| `schema.md` | `partners` table definition |
| `Endpoints.md` | Full API endpoint list |
| `Business Rules.md` | BR9: Dashboard access rules |
