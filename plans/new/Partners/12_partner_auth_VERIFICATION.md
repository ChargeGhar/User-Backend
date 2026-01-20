# Partner Auth Plan - Cross-Verification Report

**Date**: 2026-01-13  
**Plan File**: `plans/new/12_partners_auth.md`

---

## Verification Summary

| Section | Status | Notes |
|---------|--------|-------|
| Current System Analysis | ✅ ACCURATE | Matches codebase |
| Existing Infrastructure | ✅ ACCURATE | All components verified |
| User Model Constraints | ✅ ACCURATE | Password logic confirmed |
| Authentication Flows | ✅ WELL-DESIGNED | Production-grade approach |
| Database Schema | ✅ ACCURATE | Consistent with project patterns |
| API Endpoints | ✅ COMPLETE | All necessary endpoints covered |
| Serializers | ✅ CONSISTENT | Follows project patterns |
| Permission Classes | ✅ WELL-DESIGNED | Proper hierarchy |
| Service Layer | ✅ CONSISTENT | Follows BaseService pattern |
| Notification Integration | ⚠️ MINOR UPDATE | Template notification_type needs addition |
| File Structure | ⚠️ UPDATE NEEDED | You have `api/partners/auth/` separate |
| AppConfig Registration | ✅ ACCURATE | Correct pattern |
| Security Considerations | ✅ PRODUCTION-GRADE | Proper lockout, rate limiting |

---

## Detailed Verification

### 1. Existing Infrastructure ✅

| Component | Plan Says | Actual Location | Status |
|-----------|-----------|-----------------|--------|
| `BaseService` | `api/common/services/base.py` | ✅ Exists | CORRECT |
| `CRUDService` | `api/common/services/base.py` | ✅ Exists | CORRECT |
| `ServiceException` | `api/common/services/base.py` | ✅ Exists | CORRECT |
| `CustomViewRouter` | `api/common/routers.py` | ✅ Exists | CORRECT |
| `notify` | `api/user/notifications/services/notify.py` | ✅ Exists | CORRECT |
| `EmailService` | `api/user/notifications/services/email.py` | ✅ Exists | CORRECT |
| `NotificationTemplate` | `api/user/notifications/models/template.py` | ✅ Exists | CORRECT |
| `NotificationRule` | `api/user/notifications/models/rule.py` | ✅ Exists | CORRECT |
| `BaseModel` | `api/common/models/base.py` | ✅ Exists | CORRECT |
| JWT Config | `api/config/jwt.py` | ✅ Exists | CORRECT |
| Token Blacklist | `rest_framework_simplejwt.token_blacklist` | ✅ In INSTALLED_APPS | CORRECT |

### 2. User Model Password Logic ✅

**Plan says**:
```python
def set_password(self, raw_password):
    if self.is_staff or self.is_superuser:
        super().set_password(raw_password)
    else:
        pass  # Disabled for OTP-only users
```

**Actual code** (`api/user/auth/models/user.py`):
```python
def set_password(self, raw_password):
    """Allow password setting for admin users, disable for regular users"""
    if self.is_staff or self.is_superuser:
        super().set_password(raw_password)
    else:
        pass
```

**Status**: ✅ EXACT MATCH - Plan correctly identifies the constraint

### 3. JWT Configuration ✅

**Plan says**: Access: 30 days, Refresh: 90 days  
**Actual** (`api/config/jwt.py`):
```python
'ACCESS_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_ACCESS_TOKEN_DAYS', 30)))
'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_DAYS', 90)))
'ROTATE_REFRESH_TOKENS': True
'BLACKLIST_AFTER_ROTATION': True
```

**Status**: ✅ EXACT MATCH

### 4. Redis Token Pattern ✅

**Plan uses**: Redis cache with TTL (same as OTPHandler)  
**Actual OTPHandler pattern**:
```python
cache_key = f"unified_otp:{identifier}"
cache.set(cache_key, otp_data, timeout=cls.OTP_EXPIRY_MINUTES * 60)
```

**Plan proposes**:
```
Key: partner_password_setup:{token}
TTL: 86400 seconds (24 hours)
```

**Status**: ✅ CONSISTENT PATTERN

### 5. Notification System Integration ⚠️

**Plan proposes**: Use `notify()` with templates + rules

**Actual `notify()` function**:
```python
def notify(user, template_slug: str, async_send: bool = False, **context):
    # Uses NotificationTemplate.slug to find template
    # Uses NotificationRule.notification_type for channel routing
```

**Issue Found**: The `NotificationTemplate.notification_type` choices don't include `partner_email`:

```python
class NotificationTypeChoices(models.TextChoices):
    RENTAL = 'rental', 'Rental'
    PAYMENT = 'payment', 'Payment'
    PROMOTION = 'promotion', 'Promotion'
    SYSTEM = 'system', 'System'
    ACHIEVEMENT = 'achievement', 'Achievement'
    SECURITY = 'security', 'Security'
    POINTS = 'points', 'Points'
    UPDATE = 'update', 'Update'
    ADMIN = 'admin', 'Admin'
    OTP_SMS = 'otp_sms', 'OTP SMS'
    OTP_EMAIL = 'otp_email', 'OTP Email'
```

**Fix Required**: Add `PARTNER = 'partner', 'Partner'` to NotificationTypeChoices

**Updated Fixture**:
```json
{
  "model": "notifications.notificationtemplate",
  "pk": 51,
  "fields": {
    "name": "Partner Invitation",
    "slug": "partner_invitation",
    "notification_type": "partner",  // Use 'partner' instead of 'partner_email'
    ...
  }
}
```

### 6. File Structure ⚠️

**Plan proposes**:
```
api/partners/
├── common/
│   ├── services/partner_auth_service.py
│   ├── views/partner_auth_views.py
│   └── ...
```

**Actual structure**:
```
api/partners/
├── auth/           # Separate auth app (you created this)
│   └── __init__.py
├── common/
│   └── __init__.py
├── franchise/
│   └── __init__.py
└── vendor/
    └── __init__.py
```

**Recommendation**: Since you have `api/partners/auth/` as a separate app, update the plan to use:
```
api/partners/
├── auth/                              # Auth-specific
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── services/
│   │   └── partner_auth_service.py
│   ├── views/
│   │   └── partner_auth_views.py
│   └── utils/
│       └── password_token_handler.py
├── common/                            # Shared models
│   ├── models/
│   │   ├── partner.py
│   │   ├── franchise.py
│   │   └── vendor.py
│   └── ...
```

### 7. Admin Profile Service Pattern ✅

**Plan follows same pattern as** `api/admin/services/admin_profile_service.py`:
- `authenticate_admin()` → `authenticate_partner()`
- JWT token generation via `RefreshToken.for_user(user)`
- Audit logging via `AdminActionLog`

**Status**: ✅ CONSISTENT

---

## Required Updates to Plan

### Update 1: NotificationTemplate Type

Add to `api/user/notifications/models/template.py`:
```python
class NotificationTypeChoices(models.TextChoices):
    # ... existing ...
    PARTNER = 'partner', 'Partner'  # NEW
```

**Migration Required**: Yes

### Update 2: File Structure

Update plan to reflect `api/partners/auth/` as separate app:

```
api/partners/
├── __init__.py
├── auth/                              # Partner Authentication App
│   ├── __init__.py
│   ├── apps.py                        # PartnersAuthConfig
│   ├── urls.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── partner_auth_service.py
│   ├── views/
│   │   ├── __init__.py
│   │   └── partner_auth_views.py
│   └── utils/
│       ├── __init__.py
│       └── password_token_handler.py
├── common/                            # Shared Partner Models
│   ├── __init__.py
│   ├── apps.py                        # PartnersCommonConfig
│   ├── models/
│   │   ├── __init__.py
│   │   ├── partner.py                 # Partner base model
│   │   ├── franchise.py               # Franchise model
│   │   └── vendor.py                  # Vendor model
│   └── repositories/
│       └── partner_repository.py
├── franchise/                         # Franchise-specific (future)
│   └── __init__.py
└── vendor/                            # Vendor-specific (future)
    └── __init__.py
```

### Update 3: INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ... existing ...
    
    # Partner Apps
    "api.partners.common.apps.PartnersCommonConfig",
    "api.partners.auth.apps.PartnersAuthConfig",
]
```

### Update 4: Notification Fixtures

Change `notification_type` from `partner_email` to `partner`:

```json
{
  "model": "notifications.notificationtemplate",
  "pk": 51,
  "fields": {
    "slug": "partner_invitation",
    "notification_type": "partner",
    ...
  }
}
```

```json
{
  "model": "notifications.notificationrule",
  "pk": 20,
  "fields": {
    "notification_type": "partner",
    "send_in_app": false,
    "send_push": false,
    "send_sms": false,
    "send_email": true,
    "is_critical": true
  }
}
```

---

## Verification Checklist

| Item | Verified |
|------|----------|
| User model password constraint understood | ✅ |
| JWT configuration matches | ✅ |
| Redis cache pattern consistent | ✅ |
| BaseService pattern followed | ✅ |
| CustomViewRouter usage correct | ✅ |
| notify() function signature correct | ✅ |
| NotificationTemplate model understood | ✅ |
| NotificationRule model understood | ✅ |
| Admin auth pattern referenced | ✅ |
| Token blacklist available | ✅ |
| Email templates location correct | ✅ |
| File structure updated for actual layout | ⚠️ |
| NotificationType enum needs update | ⚠️ |

---

## Conclusion

Your plan is **95% accurate and production-grade**. Only minor updates needed:

1. **File structure**: Adjust for `api/partners/auth/` as separate app
2. **NotificationType**: Add `PARTNER` choice to enum
3. **Fixture notification_type**: Use `partner` instead of `partner_email`

The authentication flows, security measures, and service patterns are all consistent with the existing codebase. Ready for implementation after these minor adjustments.
