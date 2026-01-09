# ChargeGhar Project Restructuring Plan

## Overview

This document provides a comprehensive, step-by-step plan to restructure the project from the current flat structure to a modular structure with `api/user/`, `api/vendor/`, and `api/franchise/` namespaces.

---

## Current Structure

```
api/
├── admin/           # Admin panel APIs
├── common/          # Shared utilities
├── config/          # Django settings
├── content/         # CMS content
├── media/           # File uploads
├── notifications/   # Push/SMS/Email
├── payments/        # Wallet, transactions
├── points/          # Points & referrals
├── promotions/      # Coupons
├── rentals/         # Rental management
├── social/          # Achievements, leaderboard
├── stations/        # Stations & powerbanks
├── system/          # App config, countries
├── users/           # Authentication
└── web/             # WSGI/ASGI, URLs
```

---

## Target Structure

```
api/
├── admin/           # Remains as-is
├── common/          # Remains as-is
├── config/          # Remains as-is
├── web/             # Remains as-is
├── user/            # NEW: User-facing apps namespace
│   ├── __init__.py
│   ├── auth/        # Renamed from 'users'
│   ├── content/
│   ├── media/
│   ├── notifications/
│   ├── payments/
│   ├── points/
│   ├── promotions/
│   ├── rentals/
│   ├── social/
│   ├── stations/
│   └── system/
├── vendor/          # NEW: Empty module (future)
│   └── __init__.py
└── franchise/       # NEW: Empty module (future)
    └── __init__.py
```

---

## Critical Files That Need Updates

### 1. Configuration Files

| File | Changes Required |
|------|------------------|
| `api/config/application.py` | Update INSTALLED_APPS paths |
| `api/web/urls.py` | Update URL includes |
| `tasks/app.py` | Update autodiscover_tasks and task_routes |
| `api/config/social_auth.py` | Update SOCIALACCOUNT_ADAPTER path |

### 2. App Configuration Files (apps.py)

Each moved app needs its `apps.py` updated with new `name` value:

| Current | New |
|---------|-----|
| `api.users` | `api.user.auth` |
| `api.stations` | `api.user.stations` |
| `api.rentals` | `api.user.rentals` |
| `api.payments` | `api.user.payments` |
| `api.points` | `api.user.points` |
| `api.notifications` | `api.user.notifications` |
| `api.social` | `api.user.social` |
| `api.promotions` | `api.user.promotions` |
| `api.content` | `api.user.content` |
| `api.system` | `api.user.system` |
| `api.media` | `api.user.media` |

### 3. Migration Files

**CRITICAL**: All migration files contain `dependencies` that reference app labels. These MUST be updated.

Example from `api/stations/migrations/0001_initial.py`:
```python
dependencies = [
    ('media', '0001_initial'),      # Must become ('user_media', '0001_initial')
    ('rentals', '0001_initial'),    # Must become ('user_rentals', '0001_initial')
]
```

### 4. Cross-App Imports

All files with imports like `from api.users.models import User` must be updated to `from api.user.auth.models import User`.

---

## Database Considerations

### App Labels and Table Names

Django uses `app_label` for:
1. Migration tracking (`django_migrations` table)
2. Content types (`django_content_type` table)
3. Permissions (`auth_permission` table)

**Current app labels** (derived from app name):
- `users`, `stations`, `rentals`, `payments`, `points`, `notifications`, `social`, `promotions`, `content`, `system`, `media`

**Strategy**: Use explicit `label` in AppConfig to maintain backward compatibility with existing database.

Example:
```python
class AuthConfig(AppConfig):
    name = "api.user.auth"
    label = "users"  # Keep original label for DB compatibility
```

---

## Step-by-Step Execution Plan

### Phase 1: Preparation (No Code Changes)

#### Step 1.1: Backup Database
```bash
docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 1.2: Backup Codebase
```bash
git checkout -b feature/restructure-apps
git add -A && git commit -m "Backup before restructuring"
```

#### Step 1.3: Document Current State
```bash
python manage.py showmigrations > migrations_before.txt
python manage.py check > check_before.txt
```

---

### Phase 2: Create New Directory Structure

#### Step 2.1: Create Namespace Directories
```powershell
# Create user namespace
mkdir api\user

# Create empty future namespaces
mkdir api\vendor
mkdir api\franchise
```

#### Step 2.2: Create __init__.py Files
```powershell
# Create init files
echo. > api\user\__init__.py
echo. > api\vendor\__init__.py
echo. > api\franchise\__init__.py
```

---

### Phase 3: Move Apps to New Locations

#### Step 3.1: Move Apps
```powershell
# Move user-facing apps to api/user/
move api\users api\user\auth
move api\stations api\user\stations
move api\rentals api\user\rentals
move api\payments api\user\payments
move api\points api\user\points
move api\notifications api\user\notifications
move api\social api\user\social
move api\promotions api\user\promotions
move api\content api\user\content
move api\system api\user\system
move api\media api\user\media
```

---

### Phase 4: Update App Configurations

#### Step 4.1: Update api/user/auth/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class AuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.auth"
    label = "users"  # CRITICAL: Keep original label for DB compatibility
```

#### Step 4.2: Update api/user/stations/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class StationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.stations"
    label = "stations"  # CRITICAL: Keep original label
```

#### Step 4.3: Update api/user/rentals/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class RentalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.rentals"
    label = "rentals"  # CRITICAL: Keep original label
```

#### Step 4.4: Update api/user/payments/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.payments"
    label = "payments"  # CRITICAL: Keep original label
```

#### Step 4.5: Update api/user/points/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class PointsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.points"
    label = "points"  # CRITICAL: Keep original label
```

#### Step 4.6: Update api/user/notifications/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.notifications"
    label = "notifications"  # CRITICAL: Keep original label
```

#### Step 4.7: Update api/user/social/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class SocialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.social"
    label = "social"  # CRITICAL: Keep original label
```

#### Step 4.8: Update api/user/promotions/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class PromotionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.promotions"
    label = "promotions"  # CRITICAL: Keep original label
```

#### Step 4.9: Update api/user/content/apps.py
```python
from __future__ import annotations
from django.apps import AppConfig

class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.content"
    label = "content"  # CRITICAL: Keep original label
```

#### Step 4.10: Update api/user/system/apps.py
```python
from django.apps import AppConfig

class SystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.user.system'
    label = 'system'  # CRITICAL: Keep original label
    verbose_name = 'System Configuration'
    
    def ready(self):
        pass
```

#### Step 4.11: Update api/user/media/apps.py
```python
from django.apps import AppConfig

class MediaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.user.media'
    label = 'media'  # CRITICAL: Keep original label
    verbose_name = 'Media Management'
    
    def ready(self):
        pass
```

---

### Phase 5: Update Configuration Files

#### Step 5.1: Update api/config/application.py

Replace INSTALLED_APPS section:
```python
INSTALLED_APPS = [
    "admin_interface",
    "colorfield",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "corsheaders",
    "axes",
    "silk",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    # Django Allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    # PowerBank Apps - User Namespace
    "api.user.system",
    "api.user.media",
    "api.common.apps.CommonConfig",
    "api.user.auth.apps.AuthConfig",
    "api.user.stations.apps.StationsConfig",
    "api.user.rentals.apps.RentalsConfig",
    "api.user.payments.apps.PaymentsConfig",
    "api.user.points.apps.PointsConfig",
    "api.user.notifications.apps.NotificationsConfig",
    "api.user.social.apps.SocialConfig",
    "api.user.promotions.apps.PromotionsConfig",
    "api.user.content.apps.ContentConfig",
    "api.admin.apps.AdminConfig",
    "api.config.apps.ConfigConfig",
]
```

Also update SOCIALACCOUNT_ADAPTER:
```python
SOCIALACCOUNT_ADAPTER = 'api.user.auth.adapters.CustomSocialAccountAdapter'
```

#### Step 5.2: Update api/web/urls.py

Replace URL patterns:
```python
urlpatterns = [
    *_swagger_urlpatterns,
    path("", lambda _request: redirect("docs/"), name="home"),
    path("admin/", admin.site.urls),
    
    # Django Allauth URLs
    path("accounts/", include("allauth.urls")),
    
    # API app includes - User Namespace
    path("api/", include("api.user.auth.urls")),
    path("api/", include("api.user.stations.urls")),
    path("api/", include("api.user.stations.internal_urls")),
    path("api/", include("api.user.notifications.urls")),
    path("api/", include("api.user.payments.urls")),
    path("api/", include("api.user.points.urls")),
    path("api/", include("api.user.rentals.urls")),
    path("api/", include("api.user.social.urls")),
    path("api/", include("api.user.promotions.urls")),
    path("api/", include("api.user.content.urls")),
    path("api/", include("api.admin.urls")),
    path("api/", include("api.user.system.urls")),
    path("api/", include("api.user.media.urls")),
]
```

#### Step 5.3: Update tasks/app.py

Update autodiscover_tasks:
```python
app.autodiscover_tasks(
    [
        "api.user.auth",
        "api.user.stations",
        "api.user.payments",
        "api.user.points",
        "api.user.notifications",
        "api.user.rentals",
        "api.admin",
        "api.user.content",
        "api.user.social",
        "api.user.promotions",
        "api.user.system",
    ]
)
```

Update task_routes:
```python
app.conf.task_routes = {
    "api.user.auth.tasks.*": {"queue": "users"},
    "api.user.stations.tasks.*": {"queue": "stations"},
    "api.user.payments.tasks.*": {"queue": "payments"},
    "api.user.points.tasks.*": {"queue": "points"},
    "api.user.notifications.tasks.*": {"queue": "notifications"},
    "api.user.rentals.tasks.*": {"queue": "rentals"},
    "api.admin.tasks.*": {"queue": "admin"},
    "api.user.system.tasks.*": {"queue": "system"},
    "api.user.content.tasks.*": {"queue": "low_priority"},
    "api.user.social.tasks.*": {"queue": "low_priority"},
    "api.user.promotions.tasks.*": {"queue": "low_priority"},
}
```

Update beat_schedule task names:
```python
app.conf.beat_schedule = {
    "check-overdue-rentals": {
        "task": "api.user.rentals.tasks.check_overdue_rentals",
        "schedule": 60.0,
    },
    "check-offline-stations": {
        "task": "api.user.stations.tasks.check_offline_stations",
        "schedule": 300.0,
    },
    # ... update ALL task paths similarly
}
```

---

### Phase 6: Update All Import Statements

This is the most extensive phase. Every file with cross-app imports must be updated.

#### Step 6.1: Import Mapping Reference

| Old Import | New Import |
|------------|------------|
| `from api.users.models import User` | `from api.user.auth.models import User` |
| `from api.users.services` | `from api.user.auth.services` |
| `from api.stations.models` | `from api.user.stations.models` |
| `from api.rentals.models` | `from api.user.rentals.models` |
| `from api.payments.models` | `from api.user.payments.models` |
| `from api.points.models` | `from api.user.points.models` |
| `from api.notifications.services` | `from api.user.notifications.services` |
| `from api.social.models` | `from api.user.social.models` |
| `from api.promotions.models` | `from api.user.promotions.models` |
| `from api.content.models` | `from api.user.content.models` |
| `from api.system.models` | `from api.user.system.models` |
| `from api.media.models` | `from api.user.media.models` |

#### Step 6.2: Files to Update (by app)

**api/admin/** - Update all imports in:
- `api/admin/services/*.py` (all files)
- `api/admin/views/*.py` (all files)
- `api/admin/serializers/*.py` (all files)

**api/user/auth/** - Update internal imports:
- `api/user/auth/views/*.py`
- `api/user/auth/services/*.py`
- `api/user/auth/serializers/*.py`

**api/user/stations/** - Update imports:
- `api/user/stations/services/*.py`
- `api/user/stations/views/*.py`
- `api/user/stations/models/*.py`

**api/user/rentals/** - Update imports:
- `api/user/rentals/services/*.py`
- `api/user/rentals/views/*.py`
- `api/user/rentals/models/rental.py`

**api/user/payments/** - Update imports:
- `api/user/payments/services/*.py`
- `api/user/payments/views/*.py`

**api/user/points/** - Update imports:
- `api/user/points/services/*.py`
- `api/user/points/views/*.py`

**api/user/notifications/** - Update imports:
- `api/user/notifications/services/*.py`
- `api/user/notifications/views/*.py`

**api/user/social/** - Update imports:
- `api/user/social/services/*.py`
- `api/user/social/views/*.py`

**api/user/promotions/** - Update imports:
- `api/user/promotions/services/*.py`
- `api/user/promotions/views/*.py`

**api/user/content/** - Update imports:
- `api/user/content/services/*.py`
- `api/user/content/views/*.py`

**api/user/system/** - Update imports:
- `api/user/system/services/*.py`
- `api/user/system/views/*.py`

**api/user/media/** - Update imports:
- `api/user/media/services/*.py`
- `api/user/media/views.py`

---

### Phase 7: Clean Up

#### Step 7.1: Delete __pycache__ Directories
```powershell
Get-ChildItem -Path api -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

#### Step 7.2: Delete .pyc Files
```powershell
Get-ChildItem -Path api -Recurse -Filter "*.pyc" | Remove-Item -Force
```

---

### Phase 8: Verification

#### Step 8.1: Syntax Check
```bash
python -m py_compile api/config/application.py
python -m py_compile api/web/urls.py
python -m py_compile tasks/app.py
```

#### Step 8.2: Django Check
```bash
python manage.py check
```

#### Step 8.3: Migration Check
```bash
python manage.py showmigrations
```

#### Step 8.4: Import Test
```bash
python -c "from api.user.auth.models import User; print('User import OK')"
python -c "from api.user.stations.models import Station; print('Station import OK')"
python -c "from api.user.rentals.models import Rental; print('Rental import OK')"
```

---

### Phase 9: Docker Build and Test

#### Step 9.1: Rebuild Docker Images
```bash
docker compose down
docker compose build --no-cache
```

#### Step 9.2: Run Migrations
```bash
docker compose up migrations
```

#### Step 9.3: Start Services
```bash
docker compose up -d
```

#### Step 9.4: Check Logs
```bash
docker compose logs api -f
```

#### Step 9.5: Test API Endpoints
```bash
curl http://localhost:8010/api/app/health
curl http://localhost:8010/docs/
```

---

## Rollback Plan

If issues occur:

### Option 1: Git Rollback
```bash
git checkout main
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Option 2: Database Restore
```bash
docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB < backup_YYYYMMDD_HHMMSS.sql
```

---

## Post-Migration Tasks

1. Update any CI/CD pipelines with new paths
2. Update documentation
3. Update any external integrations
4. Run full test suite
5. Monitor logs for import errors

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import errors | High | High | Thorough search/replace, testing |
| Migration failures | Medium | High | Keep original app labels |
| Celery task failures | Medium | Medium | Update all task paths |
| Docker build failures | Low | Medium | Clean rebuild |

---

## Estimated Time

| Phase | Duration |
|-------|----------|
| Phase 1: Preparation | 15 min |
| Phase 2: Create Structure | 5 min |
| Phase 3: Move Apps | 10 min |
| Phase 4: Update Apps.py | 30 min |
| Phase 5: Update Config | 30 min |
| Phase 6: Update Imports | 2-4 hours |
| Phase 7: Clean Up | 5 min |
| Phase 8: Verification | 30 min |
| Phase 9: Docker Test | 30 min |
| **Total** | **4-6 hours** |

---

## Important Notes

1. **DO NOT** change app labels - this will break database migrations
2. **DO NOT** rename migration files
3. **DO NOT** modify migration dependencies (they use app labels, not paths)
4. **ALWAYS** backup before starting
5. **TEST** each phase before proceeding

---

## Appendix: Complete Import Update Script

A PowerShell script to automate import updates will be provided separately after manual verification of the plan.


---

## Appendix A: Complete Import Changes Reference

This section lists ALL files that need import updates, organized by the app they belong to.

### A.1 Files in api/admin/ (Stays in place, needs import updates)

#### api/admin/services/admin_powerbank_service.py
```python
# OLD
from api.stations.models import PowerBank, Station, StationSlot
from api.rentals.models import Rental

# NEW
from api.user.stations.models import PowerBank, Station, StationSlot
from api.user.rentals.models import Rental
```

#### api/admin/services/admin_station_service.py
```python
# OLD
from api.stations.models import (Station, StationAmenity, StationAmenityMapping, StationMedia)
from api.stations.services import StationService
from api.stations.models import PowerBank, StationSlot, StationIssue
from api.media.models import MediaUpload

# NEW
from api.user.stations.models import (Station, StationAmenity, StationAmenityMapping, StationMedia)
from api.user.stations.services import StationService
from api.user.stations.models import PowerBank, StationSlot, StationIssue
from api.user.media.models import MediaUpload
```

#### api/admin/services/station_analytics_service.py
```python
# OLD
from api.stations.models import Station, StationSlot
from api.rentals.models import Rental
from api.payments.models import Transaction

# NEW
from api.user.stations.models import Station, StationSlot
from api.user.rentals.models import Rental
from api.user.payments.models import Transaction
```

#### api/admin/serializers/station_serializers.py
```python
# OLD
from api.stations.models import PowerBank, StationMedia, Station

# NEW
from api.user.stations.models import PowerBank, StationMedia, Station
```

#### api/admin/views/payment_views.py
```python
# OLD
from api.payments.serializers import RefundSerializer
from api.users.permissions import IsStaffPermission

# NEW
from api.user.payments.serializers import RefundSerializer
from api.user.auth.permissions import IsStaffPermission
```

#### api/admin/views/points_admin_views.py
```python
# OLD
from api.users.permissions import IsStaffPermission
from api.points.serializers import PointsTransactionSerializer

# NEW
from api.user.auth.permissions import IsStaffPermission
from api.user.points.serializers import PointsTransactionSerializer
```

#### api/admin/views/referral_admin_views.py
```python
# OLD
from api.users.permissions import IsStaffPermission
from api.points.serializers import ReferralSerializer
from api.social.serializers import UserLeaderboardSerializer

# NEW
from api.user.auth.permissions import IsStaffPermission
from api.user.points.serializers import ReferralSerializer
from api.user.social.serializers import UserLeaderboardSerializer
```

#### api/admin/views/withdrawal_views.py
```python
# OLD
from api.payments.serializers import WithdrawalSerializer
from api.users.permissions import IsStaffPermission

# NEW
from api.user.payments.serializers import WithdrawalSerializer
from api.user.auth.permissions import IsStaffPermission
```

#### api/admin/tasks.py
```python
# OLD
from api.payments.models import Transaction
from api.rentals.models import Rental

# NEW
from api.user.payments.models import Transaction
from api.user.rentals.models import Rental
```

---

### A.2 Files in api/user/auth/ (moved from api/users/)

#### api/user/auth/urls.py
```python
# OLD
from api.users.views import router

# NEW
from api.user.auth.views import router
```

#### api/user/auth/views/auth_views.py
```python
# OLD
from api.users import serializers
from api.users.models import User
from api.users.services import AuthService, UserDeviceService, UserProfileService

# NEW
from api.user.auth import serializers
from api.user.auth.models import User
from api.user.auth.services import AuthService, UserDeviceService, UserProfileService
```

#### api/user/auth/views/profile_views.py
```python
# OLD
from api.users import serializers
from api.users.services import UserKYCService, UserProfileService

# NEW
from api.user.auth import serializers
from api.user.auth.services import UserKYCService, UserProfileService
```

#### api/user/auth/services/auth_service.py
```python
# OLD
from api.users.models import User
from api.users.utils.otp_handler import OTPHandler
from api.users.utils.master_otp_validator import is_master_number, validate_master_otp
from api.users.utils.verification_token_handler import VerificationTokenHandler
from api.users.utils.user_identifier_helper import is_email
from api.users.repositories import UserRepository, ProfileRepository
from api.users.services.account_service import AccountService

# NEW
from api.user.auth.models import User
from api.user.auth.utils.otp_handler import OTPHandler
from api.user.auth.utils.master_otp_validator import is_master_number, validate_master_otp
from api.user.auth.utils.verification_token_handler import VerificationTokenHandler
from api.user.auth.utils.user_identifier_helper import is_email
from api.user.auth.repositories import UserRepository, ProfileRepository
from api.user.auth.services.account_service import AccountService
```

#### api/user/auth/services/social_auth_service.py
```python
# OLD
from api.users.models import User
from api.users.repositories import UserRepository, ProfileRepository
from api.users.services.account_service import AccountService
from api.users.tasks import send_social_auth_welcome_message

# NEW
from api.user.auth.models import User
from api.user.auth.repositories import UserRepository, ProfileRepository
from api.user.auth.services.account_service import AccountService
from api.user.auth.tasks import send_social_auth_welcome_message
```

#### api/user/auth/services/account_service.py
```python
# OLD
from api.users.repositories import ProfileRepository, UserRepository
from api.payments.repositories.wallet_repository import WalletRepository
from api.points.repositories.point_repository import PointRepository

# NEW
from api.user.auth.repositories import ProfileRepository, UserRepository
from api.user.payments.repositories.wallet_repository import WalletRepository
from api.user.points.repositories.point_repository import PointRepository
```

#### api/user/auth/services/user_profile_service.py
```python
# OLD
from api.users.models import UserProfile
from api.users.repositories import ProfileRepository, UserRepository
from api.payments.repositories.wallet_repository import WalletRepository
from api.points.repositories.point_repository import PointRepository
from api.rentals.models import Rental
from api.stations.models import UserStationFavorite
from api.payments.models import Transaction

# NEW
from api.user.auth.models import UserProfile
from api.user.auth.repositories import ProfileRepository, UserRepository
from api.user.payments.repositories.wallet_repository import WalletRepository
from api.user.points.repositories.point_repository import PointRepository
from api.user.rentals.models import Rental
from api.user.stations.models import UserStationFavorite
from api.user.payments.models import Transaction
```

#### api/user/auth/services/user_device_service.py
```python
# OLD
from api.users.models import User, UserDevice
from api.users.repositories import DeviceRepository

# NEW
from api.user.auth.models import User, UserDevice
from api.user.auth.repositories import DeviceRepository
```

#### api/user/auth/services/user_kyc_service.py
```python
# OLD
from api.users.models import User, UserKYC
from api.users.repositories import ProfileRepository

# NEW
from api.user.auth.models import User, UserKYC
from api.user.auth.repositories import ProfileRepository
```

#### api/user/auth/serializers/*.py
```python
# OLD
from api.users.models import User, UserProfile, UserKYC, UserDevice
from api.users.utils.user_identifier_helper import is_email
from api.users.repositories import UserRepository

# NEW
from api.user.auth.models import User, UserProfile, UserKYC, UserDevice
from api.user.auth.utils.user_identifier_helper import is_email
from api.user.auth.repositories import UserRepository
```

#### api/user/auth/repositories/*.py
```python
# OLD
from api.users.models import User, UserProfile, UserKYC, UserDevice

# NEW
from api.user.auth.models import User, UserProfile, UserKYC, UserDevice
```

#### api/user/auth/admin.py
```python
# OLD
from api.users.models import User, UserProfile, UserKYC, UserDevice

# NEW
from api.user.auth.models import User, UserProfile, UserKYC, UserDevice
```

#### api/user/auth/adapters.py
```python
# OLD
from api.users.services import SocialAuthService
from api.users.models import UserProfile
from api.users.tasks import send_social_auth_welcome_message

# NEW
from api.user.auth.services import SocialAuthService
from api.user.auth.models import UserProfile
from api.user.auth.tasks import send_social_auth_welcome_message
```

#### api/user/auth/utils/user_identifier_helper.py
```python
# OLD
from api.users.models import User

# NEW
from api.user.auth.models import User
```

---

### A.3 Files in api/user/stations/ (moved from api/stations/)

#### api/user/stations/urls.py
```python
# OLD
from api.stations.views import router

# NEW
from api.user.stations.views import router
```

#### api/user/stations/internal_urls.py
```python
# OLD
from api.stations.views.internal_views import StationDataInternalView

# NEW
from api.user.stations.views.internal_views import StationDataInternalView
```

#### api/user/stations/views/core_views.py
```python
# OLD
from api.stations import serializers
from api.stations.models import Station
from api.stations.services import StationService

# NEW
from api.user.stations import serializers
from api.user.stations.models import Station
from api.user.stations.services import StationService
```

#### api/user/stations/views/internal_views.py
```python
# OLD
from api.users.permissions import IsStaffPermission
from api.stations.services.station_sync_service import StationSyncService
from api.stations.services.utils.sign_chargeghar_main import get_signature_util

# NEW
from api.user.auth.permissions import IsStaffPermission
from api.user.stations.services.station_sync_service import StationSyncService
from api.user.stations.services.utils.sign_chargeghar_main import get_signature_util
```

#### api/user/stations/views/user_views.py & interaction_views.py
```python
# OLD
from api.stations import serializers
from api.stations.services import StationFavoriteService, StationIssueService

# NEW
from api.user.stations import serializers
from api.user.stations.services import StationFavoriteService, StationIssueService
```

#### api/user/stations/services/*.py
```python
# OLD
from api.stations.models import (Station, StationSlot, PowerBank, UserStationFavorite, StationIssue)

# NEW
from api.user.stations.models import (Station, StationSlot, PowerBank, UserStationFavorite, StationIssue)
```

#### api/user/stations/serializers.py
```python
# OLD
from api.stations.models import (Station, StationSlot, StationAmenity, ...)

# NEW
from api.user.stations.models import (Station, StationSlot, StationAmenity, ...)
```

#### api/user/stations/admin.py
```python
# OLD
from api.stations.models import (Station, StationSlot, ...)

# NEW
from api.user.stations.models import (Station, StationSlot, ...)
```

#### api/user/stations/tasks.py
```python
# OLD
from api.stations.models import PowerBank, Station, StationSlot

# NEW
from api.user.stations.models import PowerBank, Station, StationSlot
```

---

### A.4 Files in api/user/rentals/ (moved from api/rentals/)

#### api/user/rentals/urls.py
```python
# OLD
from api.rentals.views import router

# NEW
from api.user.rentals.views import router
```

#### api/user/rentals/services/rental_service.py
```python
# OLD
from api.rentals.models import Rental, RentalExtension, RentalPackage
from api.stations.models import Station, StationSlot, PowerBank
from api.stations.services import PowerBankService

# NEW
from api.user.rentals.models import Rental, RentalExtension, RentalPackage
from api.user.stations.models import Station, StationSlot, PowerBank
from api.user.stations.services import PowerBankService
```

#### api/user/rentals/serializers/core_serializers.py
```python
# OLD
from api.rentals.models import Rental, RentalExtension, RentalIssue, RentalLocation, RentalPackage
from api.stations.models import Station

# NEW
from api.user.rentals.models import Rental, RentalExtension, RentalIssue, RentalLocation, RentalPackage
from api.user.stations.models import Station
```

---

### A.5 Files in api/user/payments/ (moved from api/payments/)

#### api/user/payments/urls.py
```python
# OLD
from api.payments.views import router

# NEW
from api.user.payments.views import router
```

#### All services, views, serializers in api/user/payments/
```python
# OLD
from api.payments.models import ...
from api.payments.services import ...
from api.rentals.models import Rental

# NEW
from api.user.payments.models import ...
from api.user.payments.services import ...
from api.user.rentals.models import Rental
```

---

### A.6 Files in api/user/points/ (moved from api/points/)

#### api/user/points/urls.py
```python
# OLD
from api.points.views import router

# NEW
from api.user.points.views import router
```

#### api/user/points/views/referrals_views.py
```python
# OLD
from api.points import serializers
from api.points.services.referral_service import ReferralService
from api.users.models import User

# NEW
from api.user.points import serializers
from api.user.points.services.referral_service import ReferralService
from api.user.auth.models import User
```

#### api/user/points/serializers.py
```python
# OLD
from api.points.models import PointsTransaction, Referral, UserPoints
from api.users.models import User

# NEW
from api.user.points.models import PointsTransaction, Referral, UserPoints
from api.user.auth.models import User
```

---

### A.7 Files in api/user/notifications/ (moved from api/notifications/)

All internal imports need `api.notifications` → `api.user.notifications`

---

### A.8 Files in api/user/social/ (moved from api/social/)

All internal imports need `api.social` → `api.user.social`

---

### A.9 Files in api/user/promotions/ (moved from api/promotions/)

All internal imports need `api.promotions` → `api.user.promotions`

---

### A.10 Files in api/user/content/ (moved from api/content/)

All internal imports need `api.content` → `api.user.content`

---

### A.11 Files in api/user/system/ (moved from api/system/)

All internal imports need `api.system` → `api.user.system`

---

### A.12 Files in api/user/media/ (moved from api/media/)

All internal imports need `api.media` → `api.user.media`

---

### A.13 Test Files (tests/)

All test files need their imports updated:
```python
# OLD
from api.users.models import User
from api.rentals.models import Rental, RentalPackage
from api.stations.models import Station, PowerBank, StationSlot
from api.payments.models import Transaction, Wallet
from api.system.models import AppConfig

# NEW
from api.user.auth.models import User
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station, PowerBank, StationSlot
from api.user.payments.models import Transaction, Wallet
from api.user.system.models import AppConfig
```

---

## Appendix B: PowerShell Script for Bulk Import Updates

Save this as `update_imports.ps1` and run after moving directories:

```powershell
# Define replacements
$replacements = @{
    'from api\.users' = 'from api.user.auth'
    'from api\.stations' = 'from api.user.stations'
    'from api\.rentals' = 'from api.user.rentals'
    'from api\.payments' = 'from api.user.payments'
    'from api\.points' = 'from api.user.points'
    'from api\.notifications' = 'from api.user.notifications'
    'from api\.social' = 'from api.user.social'
    'from api\.promotions' = 'from api.user.promotions'
    'from api\.content' = 'from api.user.content'
    'from api\.system' = 'from api.user.system'
    'from api\.media' = 'from api.user.media'
    'import api\.users' = 'import api.user.auth'
    'import api\.stations' = 'import api.user.stations'
    'import api\.rentals' = 'import api.user.rentals'
    'import api\.payments' = 'import api.user.payments'
    'import api\.points' = 'import api.user.points'
    'import api\.notifications' = 'import api.user.notifications'
    'import api\.social' = 'import api.user.social'
    'import api\.promotions' = 'import api.user.promotions'
    'import api\.content' = 'import api.user.content'
    'import api\.system' = 'import api.user.system'
    'import api\.media' = 'import api.user.media'
}

# Get all Python files
$files = Get-ChildItem -Path "api", "tests", "tasks" -Recurse -Filter "*.py"

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    $modified = $false
    
    foreach ($old in $replacements.Keys) {
        $new = $replacements[$old]
        if ($content -match $old) {
            $content = $content -replace $old, $new
            $modified = $true
        }
    }
    
    if ($modified) {
        Set-Content -Path $file.FullName -Value $content -NoNewline
        Write-Host "Updated: $($file.FullName)"
    }
}

Write-Host "Import update complete!"
```

---

## Appendix C: Verification Checklist

After completing all phases, verify:

- [ ] `python manage.py check` passes with no errors
- [ ] `python manage.py showmigrations` shows all migrations
- [ ] `python manage.py migrate --check` shows no pending migrations
- [ ] `docker compose build` succeeds
- [ ] `docker compose up` starts all services
- [ ] API health endpoint responds: `curl http://localhost:8010/api/app/health`
- [ ] Swagger docs load: `http://localhost:8010/docs/`
- [ ] Admin panel loads: `http://localhost:8010/admin/`
- [ ] Celery worker starts without import errors
- [ ] All scheduled tasks are registered (check Celery beat logs)

---

## Appendix D: Common Errors and Solutions

### Error: ModuleNotFoundError
**Cause**: Import path not updated
**Solution**: Search for the old import path and update it

### Error: App label conflict
**Cause**: Two apps have the same label
**Solution**: Ensure each app has a unique `label` in `apps.py`

### Error: Migration dependency not found
**Cause**: Migration references old app name
**Solution**: Keep original `label` in `apps.py` - DO NOT change migration files

### Error: Celery task not found
**Cause**: Task path not updated in `beat_schedule`
**Solution**: Update all task paths in `tasks/app.py`

### Error: URL pattern not found
**Cause**: URL include path not updated
**Solution**: Update paths in `api/web/urls.py`
