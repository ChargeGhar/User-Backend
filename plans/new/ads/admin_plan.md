# **ADMIN ENDPOINTS IMPLEMENTATION PLAN**
**Feature**: Advertisement System - Admin Side  
**App**: `api/admin/advertisements/`  
**Total Endpoints**: 5

---

## **PHASE 1: ADMIN SERIALIZERS**

### **Step 1.1: Create Filter Serializers**
**File**: `api/admin/serializers/ad_serializers.py`
```python
from rest_framework import serializers

class AdRequestFiltersSerializer(serializers.Serializer):
    """Filter serializer for admin ad requests list"""
    status = serializers.ChoiceField(
        choices=[
            'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED',
            'PENDING_PAYMENT', 'PAID', 'SCHEDULED', 'RUNNING',
            'PAUSED', 'COMPLETED', 'CANCELLED'
        ],
        required=False,
        allow_null=True
    )
    user_id = serializers.UUIDField(required=False, allow_null=True)
    search = serializers.CharField(required=False, allow_blank=True)
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)


class AdReviewSerializer(serializers.Serializer):
    """Serializer for reviewing and setting ad details"""
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    duration_days = serializers.IntegerField(min_value=1, max_value=365)
    admin_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    station_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    duration_seconds = serializers.IntegerField(required=False, default=5, min_value=1, max_value=30)
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)


class AdActionSerializer(serializers.Serializer):
    """Serializer for ad actions"""
    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'schedule', 'pause', 'resume', 'cancel', 'complete']
    )
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        action = attrs.get('action')
        
        # Reject action requires rejection_reason
        if action == 'reject' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required for reject action'
            })
        
        # Schedule action requires start_date
        if action == 'schedule' and not attrs.get('start_date'):
            raise serializers.ValidationError({
                'start_date': 'Start date is required for schedule action'
            })
        
        return attrs


class UpdateScheduleSerializer(serializers.Serializer):
    """Serializer for updating ad schedule"""
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    
    def validate(self, attrs):
        if not attrs.get('start_date') and not attrs.get('end_date'):
            raise serializers.ValidationError(
                'At least one of start_date or end_date must be provided'
            )
        return attrs
```

---

## **PHASE 2: ADMIN SERVICES**

### **Step 2.1: Create Admin AdRequest Service**
**File**: `api/admin/services/admin_ad_service.py`
```python
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from api.common.services.base import BaseService, ServiceException
from api.user.advertisements.models import AdRequest, AdContent, AdDistribution
from api.user.stations.models import Station

class AdminAdService(BaseService):
    """Service for admin ad operations"""
    
    def get_ad_requests(self, filters: dict):
        """Get all ad requests with filters"""
        queryset = AdRequest.objects.select_related(
            'user', 'transaction', 'reviewed_by', 'approved_by'
        ).prefetch_related(
            'adcontent_set__media_upload',
            'adcontent_set__addistribution_set__station'
        ).order_by('-created_at')
        
        # Apply filters
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('user_id'):
            queryset = queryset.filter(user_id=filters['user_id'])
        
        if filters.get('search'):
            search = filters['search']
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(full_name__icontains=search) |
                Q(user__username__icontains=search)
            )
        
        return queryset
    
    def get_ad_request_detail(self, ad_id: str) -> AdRequest:
        """Get single ad request details"""
        try:
            return AdRequest.objects.select_related(
                'user', 'transaction', 'reviewed_by', 'approved_by'
            ).prefetch_related(
                'adcontent_set__media_upload',
                'adcontent_set__addistribution_set__station'
            ).get(id=ad_id)
        except AdRequest.DoesNotExist:
            raise ServiceException(
                detail="Ad request not found",
                code="ad_not_found"
            )
    
    @transaction.atomic
    def review_ad_request(self, ad_id: str, admin_user, validated_data: dict) -> AdRequest:
        """Review ad request and set all details"""
        try:
            ad_request = AdRequest.objects.select_for_update().get(id=ad_id)
            
            # Validate status
            if ad_request.status not in ['SUBMITTED', 'UNDER_REVIEW']:
                raise ServiceException(
                    detail=f"Cannot review ad in {ad_request.status} status",
                    code="invalid_status"
                )
            
            # Validate stations exist
            station_ids = validated_data['station_ids']
            stations = Station.objects.filter(id__in=station_ids)
            if stations.count() != len(station_ids):
                raise ServiceException(
                    detail="One or more stations not found",
                    code="stations_not_found"
                )
            
            # Update AdRequest
            ad_request.status = 'UNDER_REVIEW'
            ad_request.reviewed_by = admin_user
            ad_request.reviewed_at = timezone.now()
            ad_request.title = validated_data['title']
            ad_request.description = validated_data.get('description', '')
            ad_request.duration_days = validated_data['duration_days']
            ad_request.admin_price = validated_data['admin_price']
            ad_request.admin_notes = validated_data.get('admin_notes', '')
            ad_request.start_date = validated_data.get('start_date')
            ad_request.save()
            
            # Update AdContent
            ad_content = ad_request.adcontent_set.filter(is_active=True).first()
            if ad_content:
                ad_content.duration_seconds = validated_data.get('duration_seconds', 5)
                ad_content.display_order = validated_data.get('display_order', 0)
                ad_content.save()
                
                # Clear and recreate AdDistribution records
                AdDistribution.objects.filter(ad_content=ad_content).delete()
                for station_id in station_ids:
                    AdDistribution.objects.create(
                        ad_content=ad_content,
                        station_id=station_id
                    )
            
            self.log_info(f"Ad request reviewed: {ad_request.id} by {admin_user.username}")
            return ad_request
            
        except AdRequest.DoesNotExist:
            raise ServiceException(
                detail="Ad request not found",
                code="ad_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to review ad request")
    
    @transaction.atomic
    def perform_ad_action(self, ad_id: str, admin_user, action: str, data: dict) -> AdRequest:
        """Perform action on ad request"""
        try:
            ad_request = AdRequest.objects.select_for_update().get(id=ad_id)
            
            if action == 'approve':
                return self._approve_ad(ad_request, admin_user)
            elif action == 'reject':
                return self._reject_ad(ad_request, admin_user, data['rejection_reason'])
            elif action == 'schedule':
                return self._schedule_ad(ad_request, data)
            elif action == 'pause':
                return self._pause_ad(ad_request)
            elif action == 'resume':
                return self._resume_ad(ad_request)
            elif action == 'cancel':
                return self._cancel_ad(ad_request, data.get('reason', ''))
            elif action == 'complete':
                return self._complete_ad(ad_request)
            else:
                raise ServiceException(
                    detail=f"Invalid action: {action}",
                    code="invalid_action"
                )
                
        except AdRequest.DoesNotExist:
            raise ServiceException(
                detail="Ad request not found",
                code="ad_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, f"Failed to perform action: {action}")
    
    def _approve_ad(self, ad_request: AdRequest, admin_user) -> AdRequest:
        """Approve ad request"""
        if ad_request.status != 'UNDER_REVIEW':
            raise ServiceException(
                detail="Only ads under review can be approved",
                code="invalid_status"
            )
        
        ad_request.status = 'APPROVED'
        ad_request.approved_by = admin_user
        ad_request.approved_at = timezone.now()
        ad_request.save()
        
        # Auto-transition to PENDING_PAYMENT if price is set
        if ad_request.admin_price and ad_request.admin_price > 0:
            ad_request.status = 'PENDING_PAYMENT'
            ad_request.save()
        
        self.log_info(f"Ad approved: {ad_request.id}")
        return ad_request
    
    def _reject_ad(self, ad_request: AdRequest, admin_user, reason: str) -> AdRequest:
        """Reject ad request"""
        if ad_request.status not in ['SUBMITTED', 'UNDER_REVIEW']:
            raise ServiceException(
                detail="Only submitted or under review ads can be rejected",
                code="invalid_status"
            )
        
        ad_request.status = 'REJECTED'
        ad_request.rejection_reason = reason
        ad_request.reviewed_by = admin_user
        ad_request.reviewed_at = timezone.now()
        ad_request.save()
        
        self.log_info(f"Ad rejected: {ad_request.id}")
        return ad_request
    
    def _schedule_ad(self, ad_request: AdRequest, data: dict) -> AdRequest:
        """Schedule ad to run"""
        if ad_request.status != 'PAID':
            raise ServiceException(
                detail="Only paid ads can be scheduled",
                code="invalid_status"
            )
        
        start_date = data['start_date']
        end_date = data.get('end_date')
        
        if not end_date:
            end_date = start_date + timedelta(days=ad_request.duration_days)
        
        ad_request.start_date = start_date
        ad_request.end_date = end_date
        ad_request.status = 'SCHEDULED'
        ad_request.save()
        
        self.log_info(f"Ad scheduled: {ad_request.id}")
        return ad_request
    
    def _pause_ad(self, ad_request: AdRequest) -> AdRequest:
        """Pause running ad"""
        if ad_request.status != 'RUNNING':
            raise ServiceException(
                detail="Only running ads can be paused",
                code="invalid_status"
            )
        
        ad_request.status = 'PAUSED'
        ad_request.save()
        
        self.log_info(f"Ad paused: {ad_request.id}")
        return ad_request
    
    def _resume_ad(self, ad_request: AdRequest) -> AdRequest:
        """Resume paused ad"""
        if ad_request.status != 'PAUSED':
            raise ServiceException(
                detail="Only paused ads can be resumed",
                code="invalid_status"
            )
        
        ad_request.status = 'RUNNING'
        ad_request.save()
        
        self.log_info(f"Ad resumed: {ad_request.id}")
        return ad_request
    
    def _cancel_ad(self, ad_request: AdRequest, reason: str) -> AdRequest:
        """Cancel ad"""
        if ad_request.status == 'COMPLETED':
            raise ServiceException(
                detail="Completed ads cannot be cancelled",
                code="invalid_status"
            )
        
        ad_request.status = 'CANCELLED'
        if reason:
            ad_request.admin_notes += f"\nCancellation reason: {reason}"
        ad_request.save()
        
        self.log_info(f"Ad cancelled: {ad_request.id}")
        return ad_request
    
    def _complete_ad(self, ad_request: AdRequest) -> AdRequest:
        """Complete running ad"""
        if ad_request.status != 'RUNNING':
            raise ServiceException(
                detail="Only running ads can be completed",
                code="invalid_status"
            )
        
        ad_request.status = 'COMPLETED'
        ad_request.completed_at = timezone.now()
        ad_request.save()
        
        self.log_info(f"Ad completed: {ad_request.id}")
        return ad_request
    
    @transaction.atomic
    def update_schedule(self, ad_id: str, validated_data: dict) -> AdRequest:
        """Update ad schedule"""
        try:
            ad_request = AdRequest.objects.select_for_update().get(id=ad_id)
            
            if ad_request.status not in ['SCHEDULED', 'RUNNING', 'PAUSED']:
                raise ServiceException(
                    detail="Can only update schedule for scheduled/running/paused ads",
                    code="invalid_status"
                )
            
            if validated_data.get('start_date'):
                ad_request.start_date = validated_data['start_date']
            
            if validated_data.get('end_date'):
                ad_request.end_date = validated_data['end_date']
            
            ad_request.save()
            
            self.log_info(f"Ad schedule updated: {ad_request.id}")
            return ad_request
            
        except AdRequest.DoesNotExist:
            raise ServiceException(
                detail="Ad request not found",
                code="ad_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to update schedule")
```

---

## **PHASE 3: ADMIN VIEWS**

### **Step 3.1: Create Admin Ad Views**
**File**: `api/admin/views/ad_views.py`
```python
import logging
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers as admin_serializers
from api.admin.services import AdminAdService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.user.advertisements.serializers import AdRequestDetailSerializer

admin_ads_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@admin_ads_router.register(r"admin/ads/requests", name="admin-ad-requests")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="All Ad Requests",
    description="Get list of all ad requests with filters (Staff only)",
    parameters=[admin_serializers.AdRequestFiltersSerializer],
    responses={200: BaseResponseSerializer}
)
class AdminAdRequestsView(GenericAPIView, BaseAPIView):
    """List all ad requests with filters"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all ad requests"""
        def operation():
            filter_serializer = admin_serializers.AdRequestFiltersSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminAdService()
            queryset = service.get_ad_requests(filter_serializer.validated_data)
            
            # Apply pagination
            paginated_data = self.paginate_queryset(
                queryset,
                request,
                serializer_class=AdRequestDetailSerializer
            )
            
            return paginated_data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad requests retrieved successfully",
            error_message="Failed to retrieve ad requests"
        )


@admin_ads_router.register(r"admin/ads/requests/<str:ad_id>", name="admin-ad-request-detail")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="Ad Request Details",
    description="Get detailed ad request information (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminAdRequestDetailView(GenericAPIView, BaseAPIView):
    """Get ad request details"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request, ad_id: str) -> Response:
        """Get ad request details"""
        def operation():
            service = AdminAdService()
            ad_request = service.get_ad_request_detail(ad_id)
            
            serializer = AdRequestDetailSerializer(ad_request)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad request details retrieved successfully",
            error_message="Failed to get ad request details"
        )


@admin_ads_router.register(r"admin/ads/requests/<str:ad_id>/review", name="admin-ad-review")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="Review Ad Request",
    description="Review ad request and set pricing, stations, and details (Staff only)",
    request=admin_serializers.AdReviewSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminAdReviewView(GenericAPIView, BaseAPIView):
    """Review and set ad details"""
    serializer_class = admin_serializers.AdReviewSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def patch(self, request: Request, ad_id: str) -> Response:
        """Review ad request"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminAdService()
            ad_request = service.review_ad_request(
                ad_id=ad_id,
                admin_user=request.user,
                validated_data=serializer.validated_data
            )
            
            response_serializer = AdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad request reviewed successfully",
            error_message="Failed to review ad request"
        )


@admin_ads_router.register(r"admin/ads/requests/<str:ad_id>/action", name="admin-ad-action")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="Perform Ad Action",
    description="Approve, reject, schedule, pause, resume, cancel, or complete ad (Staff only)",
    request=admin_serializers.AdActionSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminAdActionView(GenericAPIView, BaseAPIView):
    """Perform action on ad request"""
    serializer_class = admin_serializers.AdActionSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def post(self, request: Request, ad_id: str) -> Response:
        """Perform ad action"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminAdService()
            ad_request = service.perform_ad_action(
                ad_id=ad_id,
                admin_user=request.user,
                action=serializer.validated_data['action'],
                data=serializer.validated_data
            )
            
            response_serializer = AdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message=f"Ad {serializer.validated_data['action']}ed successfully",
            error_message="Failed to perform action"
        )


@admin_ads_router.register(r"admin/ads/requests/<str:ad_id>/update-schedule", name="admin-ad-update-schedule")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="Update Ad Schedule",
    description="Update start/end dates for scheduled or running ads (Staff only)",
    request=admin_serializers.UpdateScheduleSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminAdUpdateScheduleView(GenericAPIView, BaseAPIView):
    """Update ad schedule"""
    serializer_class = admin_serializers.UpdateScheduleSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def patch(self, request: Request, ad_id: str) -> Response:
        """Update ad schedule"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminAdService()
            ad_request = service.update_schedule(
                ad_id=ad_id,
                validated_data=serializer.validated_data
            )
            
            response_serializer = AdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad schedule updated successfully",
            error_message="Failed to update ad schedule"
        )
```

---

## **PHASE 4: URL REGISTRATION**

### **Step 4.1: Create URLs File**
**File**: `api/admin/advertisements/urls.py`
```python
from api.admin.views.ad_views import admin_ads_router

urlpatterns = admin_ads_router.urls
```

### **Step 4.2: Register in Main Admin URLs**
**File**: `api/admin/urls.py`
```python
# Add to urlpatterns:
path('', include('api.admin.advertisements.urls')),
```

---

## **PHASE 5: CRON JOBS / CELERY TASKS**

### **Step 5.1: Create Celery Tasks**
**File**: `api/user/advertisements/tasks.py`
```python
from celery import shared_task
from django.utils import timezone
from api.user.advertisements.models import AdRequest
import logging

logger = logging.getLogger(__name__)


@shared_task(name='advertisements.start_scheduled_ads')
def start_scheduled_ads():
    """Start ads that have reached their start date"""
    today = timezone.now().date()
    
    ads_to_start = AdRequest.objects.filter(
        status='SCHEDULED',
        start_date__lte=today
    )
    
    count = 0
    for ad in ads_to_start:
        ad.status = 'RUNNING'
        ad.save(update_fields=['status', 'updated_at'])
        count += 1
        logger.info(f"Started ad: {ad.id}")
    
    logger.info(f"Started {count} scheduled ads")
    return count


@shared_task(name='advertisements.complete_finished_ads')
def complete_finished_ads():
    """Complete ads that have passed their end date"""
    today = timezone.now().date()
    
    ads_to_complete = AdRequest.objects.filter(
        status='RUNNING',
        end_date__lt=today
    )
    
    count = 0
    for ad in ads_to_complete:
        ad.status = 'COMPLETED'
        ad.completed_at = timezone.now()
        ad.save(update_fields=['status', 'completed_at', 'updated_at'])
        count += 1
        logger.info(f"Completed ad: {ad.id}")
    
    logger.info(f"Completed {count} finished ads")
    return count
```

### **Step 5.2: Register Celery Beat Schedule**
**File**: `api/config/celery.py`
```python
# Add to beat_schedule:
'start-scheduled-ads': {
    'task': 'advertisements.start_scheduled_ads',
    'schedule': crontab(minute=0),  # Every hour
},
'complete-finished-ads': {
    'task': 'advertisements.complete_finished_ads',
    'schedule': crontab(minute=0),  # Every hour
},
```

---

## **PHASE 6: TESTING**

### **Step 6.1: Test Admin Endpoints**
```bash
# 1. List all ad requests
GET /api/admin/ads/requests
GET /api/admin/ads/requests?status=SUBMITTED
GET /api/admin/ads/requests?search=test

# 2. Get ad details
GET /api/admin/ads/requests/{ad_id}

# 3. Review ad
PATCH /api/admin/ads/requests/{ad_id}/review
{
  "title": "Summer Sale",
  "description": "50% off",
  "duration_days": 30,
  "admin_price": "5000.00",
  "station_ids": ["uuid1", "uuid2"],
  "duration_seconds": 7
}

# 4. Approve ad
POST /api/admin/ads/requests/{ad_id}/action
{"action": "approve"}

# 5. Schedule ad
POST /api/admin/ads/requests/{ad_id}/action
{
  "action": "schedule",
  "start_date": "2026-01-20"
}

# 6. Update schedule
PATCH /api/admin/ads/requests/{ad_id}/update-schedule
{
  "start_date": "2026-01-25",
  "end_date": "2026-02-25"
}
```

---

## **CHECKLIST**

- [ ] Admin serializers created (filters, review, action, schedule)
- [ ] AdminAdService implemented with all actions
- [ ] All 5 admin views created
- [ ] URLs registered
- [ ] Celery tasks created for auto start/complete
- [ ] Celery beat schedule configured
- [ ] All endpoints tested
- [ ] Status transitions validated
- [ ] Error handling tested
- [ ] Permissions working (IsStaffPermission)
- [ ] Pagination working for list endpoint
- [ ] Search and filters working
