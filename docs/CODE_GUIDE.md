# ChargeGhar Code Guide

## Project Architecture Overview

This guide defines the coding standards, patterns, and architecture for the ChargeGhar PowerBank rental platform. Follow these patterns to ensure consistency, maintainability, and error-free code.

### Core Architecture Principles

1. **Service Layer Pattern**: Business logic resides in services (`api/{app}/services/`)
2. **Standardized Responses**: All APIs use consistent response format via mixins
3. **Common Components**: Shared functionality in `api/common/` (services, mixins, decorators)
4. **Error Handling**: Centralized exception handling with context-aware messages
5. **Routing**: Custom router system for clean URL organization

## Directory Structure

```
api/
├── common/                 # Shared components
│   ├── services/base.py   # Base service classes
│   ├── mixins.py          # View mixins for standard responses
│   ├── decorators.py      # Common decorators (rate_limit, log_api_call)
│   ├── exceptions/        # Custom exceptions
│   └── utils/helpers.py   # Utility functions
├── {app}/                 # App-specific code
│   ├── models.py          # Django models
│   ├── serializers.py     # DRF serializers
│   ├── views/             # View modules
│   └── services/          # Business logic services
```

## Service Layer Implementation

### Base Service Classes

All services inherit from base classes in `api/common/services/base.py`:

**BaseService**: Foundation with logging and error handling
**CRUDService**: Extends BaseService with CRUD operations
**ServiceException**: Enhanced exception with context and user messages

### Service Structure Pattern

```python
from api.common.services.base import BaseService, ServiceException

class {Entity}Service(BaseService):
    """Service for {entity} operations"""
    
    def __init__(self):
        super().__init__()
        # Service-specific initialization
    
    def operation_name(self, param: type) -> ReturnType:
        """Operation description"""
        try:
            # Business logic implementation
            result = self._perform_operation(param)
            
            self.log_info(f"Operation completed: {param}")
            return result
            
        except Exception as e:
            self.handle_service_error(e, "Operation context")
```

### Enhanced Error Handling

```python
# In services - use ServiceException with context
raise ServiceException(
    detail="User-friendly error message",
    code="error_code",
    status_code=status.HTTP_400_BAD_REQUEST,
    context={'field': 'value'},
    user_message="Message shown to user"
)
```

## View Implementation

### Base View Pattern

All views inherit from `BaseAPIView` which combines essential mixins:

```python
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.decorators import log_api_call, rate_limit

{app}_router = CustomViewRouter()

@{app}_router.register(r"endpoint/path", name="endpoint-name")
@extend_schema(
    tags=["{App}"],
    summary="Operation Summary",
    description="Detailed description",
    responses={200: ResponseSerializer}
)
class {Operation}View(GenericAPIView, BaseAPIView):
    serializer_class = {Request}Serializer
    permission_classes = [IsAuthenticated]  # or [AllowAny]
    
    @log_api_call(include_request_data=True)
    @rate_limit(max_requests=5, window_seconds=300)  # Optional
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        def operation():
            service = {Entity}Service()
            return service.operation_method(
                **serializer.validated_data
            )
        
        return self.handle_service_operation(
            operation,
            success_message="Operation successful",
            error_message="Operation failed",
            operation_context="Operation name"
        )
```

### Available Mixins

**StandardResponseMixin**: `success_response()`, `error_response()`
**ServiceHandlerMixin**: `handle_service_operation()` with enhanced error handling
**PaginationMixin**: `paginate_response()`, `get_pagination_params()`
**CacheableMixin**: `get_cached_data()`, `get_cache_key()`
**FilterMixin**: `apply_date_filters()`, `apply_status_filter()`

## Serializer Patterns

### Request Serializers

```python
class {Operation}Serializer(serializers.Serializer):
    """Serializer for {operation} request"""
    field_name = serializers.CharField(help_text="Field description")
    
    def validate_field_name(self, value):
        """Custom field validation"""
        if not condition:
            raise serializers.ValidationError("Validation message")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        if attrs.get('field1') and not attrs.get('field2'):
            raise serializers.ValidationError("Field2 required when field1 provided")
        return attrs
```

### Model Serializers

```python
class {Model}Serializer(serializers.ModelSerializer):
    """Serializer for {model}"""
    
    class Meta:
        model = {Model}
        fields = ['id', 'field1', 'field2', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_field(self, value):
        """Field-specific validation"""
        return value
```

## Common Decorators

### Available Decorators

```python
@log_api_call(include_request_data=True)
@rate_limit(max_requests=5, window_seconds=300)
@cached_response(timeout=300, key_func=custom_key_func)
@require_complete_profile
@require_kyc_verified
```

## Error Handling Standards

### Custom Exceptions

Use predefined exceptions from `api/common/exceptions/custom.py`:

- `ProfileIncompleteException`
- `KYCNotVerifiedException`
- `InsufficientBalanceException`
- `ActiveRentalExistsException`
- `PaymentFailedException`
- `InvalidOTPException`
- `RateLimitExceededException`

### Service Error Handling

```python
# In services
try:
    # Operation
    pass
except SpecificException as e:
    raise ServiceException(
        detail="User-friendly message",
        code="specific_error",
        context={'additional': 'info'},
        user_message="Message for frontend"
    )
except Exception as e:
    self.handle_service_error(e, "Operation context")
```

## Response Standards

### Success Response Format

```json
{
    "success": true,
    "message": "Operation successful",
    "data": {...}
}
```

### Error Response Format

```json
{
    "success": false,
    "error": {
        "code": "error_code",
        "message": "User-friendly message",
        "context": {...}
    }
}
```

### Paginated Response Format

```json
{
    "success": true,
    "message": "Data retrieved successfully",
    "data": {
        "results": [...],
        "pagination": {
            "current_page": 1,
            "total_pages": 5,
            "total_count": 100,
            "page_size": 20,
            "has_next": true,
            "has_previous": false
        }
    }
}
```

## Utility Functions

### Common Helpers (`api/common/utils/helpers.py`)

```python
# Code generation
generate_random_code(length=6, include_letters=True, include_numbers=True)
generate_unique_code(prefix="", length=8)
generate_transaction_id()

# Validation
validate_phone_number(phone)
mask_sensitive_data(data, mask_char="*", visible_chars=4)

# Pagination
paginate_queryset(queryset, page=1, page_size=20)

# Calculations
calculate_points_from_amount(amount, points_per_unit=10)
calculate_distance(lat1, lon1, lat2, lon2)
```

## Model Patterns

### Base Model

All models inherit from `BaseModel` which provides:
- `id` (UUID primary key)
- `created_at` (auto timestamp)
- `updated_at` (auto timestamp)

### Model Structure

```python
from api.common.models import BaseModel

class {Entity}(BaseModel):
    """Model description"""
    
    # Fields
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        db_table = '{app}_{entity}'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
```

## Testing Patterns

### Service Tests

```python
from django.test import TestCase
from api.{app}.services import {Entity}Service

class {Entity}ServiceTest(TestCase):
    def setUp(self):
        self.service = {Entity}Service()
    
    def test_operation_success(self):
        result = self.service.operation(valid_data)
        self.assertIsNotNone(result)
    
    def test_operation_failure(self):
        with self.assertRaises(ServiceException):
            self.service.operation(invalid_data)
```

## File Organization Rules

### Service Files
- Location: `api/{app}/services/{entity}_service.py`
- Class name: `{Entity}Service`
- Inherit from: `BaseService` or `CRUDService`

### View Files
- Location: `api/{app}/views/{entity}_views.py`
- Router name: `{app}_router`
- Class name: `{Operation}View`

### Serializer Files
- Location: `api/{app}/serializers.py`
- Request serializers: `{Operation}Serializer`
- Model serializers: `{Model}Serializer`

## Import Standards

```python
# Standard library imports
from __future__ import annotations
import logging
from typing import Dict, Any, Optional

# Django imports
from django.db import transaction
from django.utils import timezone

# DRF imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request

# Project imports
from api.common.services.base import BaseService, ServiceException
from api.common.mixins import BaseAPIView
from api.{app}.models import {Model}
```

## Logging Standards

```python
# In services
self.log_info(f"Operation completed: {param}")
self.log_error(f"Operation failed: {error}")
self.log_warning(f"Warning condition: {condition}")

# In views - automatic via @log_api_call decorator
@log_api_call(include_request_data=True)
```

## Cache Usage

```python
# In services
from django.core.cache import cache

cache_key = f"entity_{entity_id}"
cached_data = cache.get(cache_key)
if cached_data is None:
    cached_data = self.fetch_data()
    cache.set(cache_key, cached_data, timeout=3600)

# In views - using CacheableMixin
cache_key = self.get_cache_key(param1, param2)
data = self.get_cached_data(cache_key, fetch_function)
```

## Database Transaction Handling

```python
# In services
from django.db import transaction

@transaction.atomic
def complex_operation(self, data):
    # Multiple database operations
    pass

# Or using base service method
def operation(self, data):
    return self.execute_with_transaction(
        self._perform_operation, data
    )
```

## API Documentation Standards

```python
@extend_schema(
    tags=["App Name"],
    summary="Brief operation description",
    description="Detailed operation description with examples",
    request=RequestSerializer,
    responses={
        200: ResponseSerializer,
        400: "Bad request - validation errors",
        401: "Authentication required",
        403: "Permission denied",
        404: "Resource not found"
    },
    examples=[
        OpenApiExample(
            "Success Example",
            value={"field": "value"},
            request_only=True
        )
    ]
)
```

# Module Organization & __init__.py Files

### Services __init__.py Pattern

**Location**: `api/{app}/services/__init__.py`

```python
"""
Services package for {app} app
============================================================

This package contains all service classes organized by functionality.
Maintains backward compatibility by re-exporting all services.

Auto-generated by Service Separator
Date: {current_date}
"""
from __future__ import annotations

from .{entity}_service import {Entity}Service
# Import all service classes

# Backward compatibility - all services available at package level
__all__ = [
    "{Entity}Service",
    # List all service classes
]
```

### Views __init__.py Pattern

**Location**: `api/{app}/views/__init__.py`

```python
"""
Views package for {app} app
Maintains backward compatibility by exposing single router
"""
from __future__ import annotations

from api.common.routers import CustomViewRouter

from .{entity}_views import {entity}_router
# Import all view routers

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [{entity}_router, ...]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)
```

### URLs Pattern

**Location**: `api/{app}/urls.py`

```python
from __future__ import annotations

from api.{app}.views import router

urlpatterns = [
    *router.urls,
]
```