# **USER ENDPOINTS IMPLEMENTATION PLAN**
**Feature**: Advertisement System - User Side  
**App**: `api/user/advertisements/`  
**Total Endpoints**: 3

---

## **PHASE 1: SETUP & MODELS**

### **Step 1.1: Create App Structure**
```bash
mkdir -p api/user/advertisements
mkdir -p api/user/advertisements/models
mkdir -p api/user/advertisements/services
mkdir -p api/user/advertisements/serializers
mkdir -p api/user/advertisements/views
mkdir -p api/user/advertisements/repositories
```

### **Step 1.2: Create Models**
**File**: `api/user/advertisements/models/__init__.py`
```python
from .ad_request import AdRequest
from .ad_content import AdContent
from .ad_distribution import AdDistribution

__all__ = ['AdRequest', 'AdContent', 'AdDistribution']
```

**File**: `api/user/advertisements/models/ad_request.py`
- Copy from `plans/new/ads/06_advertisement.md` (AdRequest model)
- Add indexes as specified
- Ensure all ForeignKey relationships are correct

**File**: `api/user/advertisements/models/ad_content.py`
- Copy from `plans/new/ads/06_advertisement.md` (AdContent model)
- Add indexes as specified

**File**: `api/user/advertisements/models/ad_distribution.py`
- Copy from `plans/new/ads/06_advertisement.md` (AdDistribution model)
- Add indexes as specified

### **Step 1.3: Update Transaction Model**
**File**: `api/user/payments/models/transaction.py`
```python
# Add to TRANSACTION_TYPE_CHOICES:
('ADVERTISEMENT', 'Advertisement'),
```

### **Step 1.4: Register Models in Admin**
**File**: `api/user/advertisements/admin.py`

---

## **PHASE 2: REPOSITORIES**

### **Step 2.1: Create AdRequest Repository**
**File**: `api/user/advertisements/repositories/ad_request_repository.py`
```python
from typing import Optional, List
from django.db.models import QuerySet
from api.user.advertisements.models import AdRequest

class AdRequestRepository:
    """Repository for AdRequest data operations"""
    
    @staticmethod
    def get_by_id(ad_id: str) -> Optional[AdRequest]:
        """Get ad request by ID"""
        try:
            return AdRequest.objects.select_related(
                'user', 'transaction', 'reviewed_by', 'approved_by'
            ).prefetch_related(
                'adcontent_set__media_upload',
                'adcontent_set__addistribution_set__station'
            ).get(id=ad_id)
        except AdRequest.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_ad_requests(user, status: str = None) -> QuerySet:
        """Get user's ad requests with optional status filter"""
        queryset = AdRequest.objects.filter(user=user).select_related(
            'transaction', 'reviewed_by', 'approved_by'
        ).prefetch_related(
            'adcontent_set__media_upload',
            'adcontent_set__addistribution_set__station'
        ).order_by('-created_at')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    @staticmethod
    def create(user, **kwargs) -> AdRequest:
        """Create new ad request"""
        return AdRequest.objects.create(user=user, **kwargs)
```

### **Step 2.2: Create AdContent Repository**
**File**: `api/user/advertisements/repositories/ad_content_repository.py`
```python
from typing import Optional
from api.user.advertisements.models import AdContent

class AdContentRepository:
    """Repository for AdContent data operations"""
    
    @staticmethod
    def create(ad_request, **kwargs) -> AdContent:
        """Create new ad content"""
        return AdContent.objects.create(ad_request=ad_request, **kwargs)
    
    @staticmethod
    def get_by_ad_request(ad_request_id: str) -> Optional[AdContent]:
        """Get ad content by ad request ID"""
        return AdContent.objects.filter(
            ad_request_id=ad_request_id,
            is_active=True
        ).select_related('media_upload').first()
```

---

## **PHASE 3: SERIALIZERS**

### **Step 3.1: Create Action Serializers (Request Payloads)**
**File**: `api/user/advertisements/serializers/action_serializers.py`
```python
from rest_framework import serializers
from api.user.media.models import MediaUpload

class AdRequestCreateSerializer(serializers.Serializer):
    """Request serializer for creating ad request"""
    full_name = serializers.CharField(max_length=255)
    contact_number = serializers.CharField(max_length=50)
    media_upload_id = serializers.UUIDField()
    
    def validate_media_upload_id(self, value):
        """Validate media upload exists and belongs to user"""
        request = self.context.get('request')
        try:
            media = MediaUpload.objects.get(id=value, uploaded_by=request.user)
            if media.file_type not in ['IMAGE', 'VIDEO']:
                raise serializers.ValidationError("Only IMAGE or VIDEO files allowed")
            return value
        except MediaUpload.DoesNotExist:
            raise serializers.ValidationError("Media upload not found")

class AdPaymentSerializer(serializers.Serializer):
    """Request serializer for ad payment (empty - uses URL param)"""
    pass
```

### **Step 3.2: Create Response Serializers**
**File**: `api/user/advertisements/serializers/detail_serializers.py`
```python
from rest_framework import serializers
from api.user.advertisements.models import AdRequest, AdContent, AdDistribution
from api.user.media.serializers import MediaUploadSerializer
from api.user.stations.serializers import StationBasicSerializer

class AdContentDetailSerializer(serializers.ModelSerializer):
    """Detailed ad content serializer"""
    media_upload = MediaUploadSerializer(read_only=True)
    
    class Meta:
        model = AdContent
        fields = ['id', 'content_type', 'media_upload', 'duration_seconds', 
                  'display_order', 'is_active']

class AdRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed ad request serializer"""
    ad_content = serializers.SerializerMethodField()
    stations = serializers.SerializerMethodField()
    
    class Meta:
        model = AdRequest
        fields = ['id', 'full_name', 'contact_number', 'title', 'description',
                  'status', 'duration_days', 'admin_price', 'submitted_at',
                  'approved_at', 'paid_at', 'start_date', 'end_date',
                  'rejection_reason', 'admin_notes', 'ad_content', 'stations']
    
    def get_ad_content(self, obj):
        content = obj.adcontent_set.filter(is_active=True).first()
        if content:
            return AdContentDetailSerializer(content).data
        return None
    
    def get_stations(self, obj):
        content = obj.adcontent_set.filter(is_active=True).first()
        if content:
            stations = [dist.station for dist in content.addistribution_set.all()]
            return StationBasicSerializer(stations, many=True).data
        return []
```

### **Step 3.3: Create List Serializers**
**File**: `api/user/advertisements/serializers/list_serializers.py`
```python
from rest_framework import serializers
from api.user.advertisements.models import AdRequest

class AdRequestListSerializer(serializers.ModelSerializer):
    """List serializer for ad requests"""
    ad_content = serializers.SerializerMethodField()
    stations_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AdRequest
        fields = ['id', 'title', 'status', 'admin_price', 'submitted_at',
                  'start_date', 'end_date', 'ad_content', 'stations_count']
    
    def get_ad_content(self, obj):
        from .detail_serializers import AdContentDetailSerializer
        content = obj.adcontent_set.filter(is_active=True).first()
        if content:
            return AdContentDetailSerializer(content).data
        return None
    
    def get_stations_count(self, obj):
        content = obj.adcontent_set.filter(is_active=True).first()
        if content:
            return content.addistribution_set.count()
        return 0
```

---

## **PHASE 4: SERVICES**

### **Step 4.1: Create AdRequest Service**
**File**: `api/user/advertisements/services/ad_request_service.py`
```python
from django.db import transaction
from django.utils import timezone
from api.common.services.base import BaseService, ServiceException
from api.user.advertisements.models import AdRequest, AdContent
from api.user.advertisements.repositories import AdRequestRepository, AdContentRepository
from api.user.media.models import MediaUpload

class AdRequestService(BaseService):
    """Service for ad request operations"""
    
    @transaction.atomic
    def create_ad_request(self, user, validated_data: dict) -> AdRequest:
        """Create new ad request with content"""
        try:
            # Get and validate media upload
            media_upload = MediaUpload.objects.get(
                id=validated_data['media_upload_id'],
                uploaded_by=user
            )
            
            if media_upload.file_type not in ['IMAGE', 'VIDEO']:
                raise ServiceException(
                    detail="Only IMAGE or VIDEO files are allowed",
                    code="invalid_media_type"
                )
            
            # Create AdRequest
            ad_request = AdRequestRepository.create(
                user=user,
                full_name=validated_data['full_name'],
                contact_number=validated_data['contact_number'],
                status='SUBMITTED',
                submitted_at=timezone.now()
            )
            
            # Create AdContent
            AdContentRepository.create(
                ad_request=ad_request,
                media_upload=media_upload,
                content_type=media_upload.file_type,
                is_active=True,
                duration_seconds=5,
                display_order=0
            )
            
            self.log_info(f"Ad request created: {ad_request.id} by {user.username}")
            return ad_request
            
        except MediaUpload.DoesNotExist:
            raise ServiceException(
                detail="Media upload not found or access denied",
                code="media_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to create ad request")
    
    def get_user_ad_requests(self, user, filters: dict = None):
        """Get user's ad requests with optional filtering"""
        status = filters.get('status') if filters else None
        return AdRequestRepository.get_user_ad_requests(user, status)
```

### **Step 4.2: Create AdPayment Service**
**File**: `api/user/advertisements/services/ad_payment_service.py`
```python
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from api.common.services.base import BaseService, ServiceException
from api.common.utils.codes import generate_transaction_id
from api.user.advertisements.models import AdRequest
from api.user.payments.models import Transaction, Wallet, WalletTransaction

class AdPaymentService(BaseService):
    """Service for ad payment operations"""
    
    @transaction.atomic
    def process_ad_payment(self, ad_request_id: str, user) -> AdRequest:
        """Process payment for approved ad request"""
        try:
            # Get ad request with row-level lock
            ad_request = AdRequest.objects.select_for_update().get(
                id=ad_request_id,
                user=user
            )
            
            # Validate status
            if ad_request.status != 'PENDING_PAYMENT':
                raise ServiceException(
                    detail=f"Ad is not pending payment. Current status: {ad_request.status}",
                    code="invalid_ad_status"
                )
            
            # Validate price is set
            if not ad_request.admin_price or ad_request.admin_price <= 0:
                raise ServiceException(
                    detail="Admin price not set for this ad",
                    code="price_not_set"
                )
            
            # Get user wallet
            try:
                wallet = Wallet.objects.select_for_update().get(
                    user=user,
                    is_active=True
                )
            except Wallet.DoesNotExist:
                raise ServiceException(
                    detail="User wallet not found or inactive",
                    code="wallet_not_found"
                )
            
            # Check sufficient balance
            if wallet.balance < ad_request.admin_price:
                raise ServiceException(
                    detail=f"Insufficient balance. Required: NPR {ad_request.admin_price}, Available: NPR {wallet.balance}",
                    code="insufficient_balance"
                )
            
            # Create Transaction record
            txn = Transaction.objects.create(
                user=user,
                transaction_id=generate_transaction_id(),
                transaction_type='ADVERTISEMENT',
                amount=ad_request.admin_price,
                currency='NPR',
                status='SUCCESS',
                payment_method_type='WALLET',
                gateway_response={
                    'ad_request_id': str(ad_request.id),
                    'ad_title': ad_request.title or 'Advertisement'
                }
            )
            
            # Create WalletTransaction for audit trail
            balance_before = wallet.balance
            balance_after = wallet.balance - ad_request.admin_price
            
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction=txn,
                transaction_type='DEBIT',
                amount=ad_request.admin_price,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f'Payment for advertisement: {ad_request.title or ad_request.id}',
                metadata={
                    'ad_request_id': str(ad_request.id),
                    'payment_type': 'ad_payment'
                }
            )
            
            # Update wallet balance
            wallet.balance = balance_after
            wallet.save(update_fields=['balance', 'updated_at'])
            
            # Update ad request
            ad_request.transaction = txn
            ad_request.paid_at = timezone.now()
            ad_request.status = 'PAID'
            ad_request.save(update_fields=['transaction', 'paid_at', 'status', 'updated_at'])
            
            self.log_info(
                f"Ad payment processed: {ad_request.id} - NPR {ad_request.admin_price} by {user.username}"
            )
            
            return ad_request
            
        except AdRequest.DoesNotExist:
            raise ServiceException(
                detail="Ad request not found or access denied",
                code="ad_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to process ad payment")
```

---

## **PHASE 5: VIEWS**

### **Step 5.1: Create Core Views**
**File**: `api/user/advertisements/views/core_views.py`
```python
import logging
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.advertisements import serializers
from api.user.advertisements.services import AdRequestService, AdPaymentService

ads_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@ads_router.register(r"user/ads/request", name="ad-request-create")
@extend_schema(
    tags=["Advertisements - User"],
    summary="Submit Ad Request",
    description="Submit new advertisement request with media",
    responses={201: BaseResponseSerializer}
)
class AdRequestCreateView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdRequestCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Submit new ad request"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdRequestService()
            ad_request = service.create_ad_request(
                user=request.user,
                validated_data=serializer.validated_data
            )
            
            response_serializer = serializers.AdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad request submitted successfully",
            error_message="Failed to submit ad request",
            success_status=status.HTTP_201_CREATED
        )


@ads_router.register(r"user/ads/my-ads", name="my-ad-requests")
@extend_schema(
    tags=["Advertisements - User"],
    summary="My Ad Requests",
    description="Get list of user's ad requests with optional status filter",
    responses={200: BaseResponseSerializer}
)
class MyAdRequestsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdRequestListSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user's ad requests"""
        def operation():
            filters = {
                'status': request.query_params.get('status')
            }
            
            service = AdRequestService()
            queryset = service.get_user_ad_requests(request.user, filters)
            
            # Apply pagination
            paginated_data = self.paginate_queryset(
                queryset,
                request,
                serializer_class=self.serializer_class
            )
            
            return paginated_data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad requests retrieved successfully",
            error_message="Failed to retrieve ad requests"
        )


@ads_router.register(r"user/ads/<str:ad_id>/pay", name="ad-payment")
@extend_schema(
    tags=["Advertisements - User"],
    summary="Pay for Ad",
    description="Process payment for approved advertisement using wallet balance",
    responses={200: BaseResponseSerializer}
)
class AdPaymentView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def post(self, request: Request, ad_id: str) -> Response:
        """Process ad payment"""
        def operation():
            service = AdPaymentService()
            ad_request = service.process_ad_payment(
                ad_request_id=ad_id,
                user=request.user
            )
            
            response_serializer = serializers.AdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Payment processed successfully",
            error_message="Failed to process payment"
        )
```

---

## **PHASE 6: URL REGISTRATION**

### **Step 6.1: Create URLs File**
**File**: `api/user/advertisements/urls.py`
```python
from api.user.advertisements.views.core_views import ads_router

urlpatterns = ads_router.urls
```

### **Step 6.2: Register in Main URLs**
**File**: `api/user/urls.py`
```python
# Add to urlpatterns:
path('', include('api.user.advertisements.urls')),
```

---

## **PHASE 7: MIGRATIONS & TESTING**

### **Step 7.1: Create Migrations**
```bash
python manage.py makemigrations advertisements
python manage.py migrate
```

### **Step 7.2: Test Endpoints**
```bash
# 1. Submit ad request
POST /api/user/ads/request
{
  "full_name": "Test User",
  "contact_number": "+977-9841234567",
  "media_upload_id": "uuid"
}

# 2. Get my ads
GET /api/user/ads/my-ads
GET /api/user/ads/my-ads?status=SUBMITTED

# 3. Pay for ad
POST /api/user/ads/{ad_id}/pay
```

---

## **CHECKLIST**

- [ ] Models created and migrated
- [ ] Transaction model updated with ADVERTISEMENT type
- [ ] Repositories implemented
- [ ] Serializers created (action, detail, list)
- [ ] Services implemented with proper error handling
- [ ] Views created with proper decorators
- [ ] URLs registered
- [ ] All 3 endpoints tested
- [ ] Response structure matches specification
- [ ] Error handling tested
- [ ] Pagination working for list endpoint
