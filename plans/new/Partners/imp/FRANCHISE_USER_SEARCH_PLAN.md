# PLAN: Franchise User Search Endpoint

## OBJECTIVE
Add missing endpoint: `GET /api/partner/franchise/users/search/` for franchises to search users when creating vendors.

## CURRENT STATE
- ✅ Admin has: `GET /api/admin/users/` (AdminUserService.get_users_list)
- ❌ Franchise missing: `GET /api/partner/franchise/users/search/`

## REQUIREMENT (from Endpoints.md)
```
GET /api/partner/franchise/users/search/
- Search users for vendor creation
- Query params: ?search={email|phone|name}&exclude_partners=true
- Returns: Minimal user data (id, email, phone, username)
```

## CONSISTENCY CHECK (AdminUserService)
```python
# api/admin/services/admin_user_service.py
def get_users_list(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    queryset = User.objects.select_related('profile', 'kyc', 'wallet', 'points')
    
    # Filters:
    - status
    - search (username, email, phone_number)
    - start_date, end_date
    
    # Returns: Paginated queryset
```

## IMPLEMENTATION PLAN

### 1. Create Service (franchise_user_service.py)
**Location:** `api/partners/franchise/services/franchise_user_service.py`

**Method:** `search_users_for_vendor(filters: Dict) -> Dict`

**Logic:**
```python
- Query: User.objects.select_related('profile').filter(is_active=True)
- Search: username, email, phone_number (like admin)
- Exclude partners: if exclude_partners=true, exclude users with partner_profile
- Return: User fields + profile data
- Pagination: page, page_size
```

**Fields to Return:**
```python
{
    'id': user.id,
    'email': user.email,
    'phone_number': user.phone_number,
    'username': user.username,
    'profile_picture': user.profile_picture,
    'status': user.status,
    'is_partner': hasattr(user, 'partner_profile'),
    'profile': {
        'full_name': user.profile.full_name if hasattr(user, 'profile') else None,
        'date_of_birth': user.profile.date_of_birth if hasattr(user, 'profile') else None,
        'address': user.profile.address if hasattr(user, 'profile') else None,
        'avatar_url': user.profile.avatar_url if hasattr(user, 'profile') else None,
        'is_profile_complete': user.profile.is_profile_complete if hasattr(user, 'profile') else False,
    } if hasattr(user, 'profile') else None
}
```

### 2. Create Serializer (user_serializers.py)
**Location:** `api/partners/franchise/serializers/user_serializers.py`

**Serializers:**
```python
class UserProfileDataSerializer(serializers.Serializer):
    """User profile data"""
    full_name = serializers.CharField(allow_null=True)
    date_of_birth = serializers.DateField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    avatar_url = serializers.URLField(allow_null=True)
    is_profile_complete = serializers.BooleanField()

class UserSearchResultSerializer(serializers.Serializer):
    """Minimal user data for vendor creation"""
    id = serializers.IntegerField()
    email = serializers.EmailField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    username = serializers.CharField(allow_null=True)
    profile_picture = serializers.URLField(allow_null=True)
    status = serializers.CharField()
    is_partner = serializers.BooleanField()
    profile = UserProfileDataSerializer(allow_null=True)

class UserSearchListSerializer(serializers.Serializer):
    """Paginated user search results"""
    results = UserSearchResultSerializer(many=True)
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
```

### 3. Create View (franchise_user_view.py)
**Location:** `api/partners/franchise/views/franchise_user_view.py`

**Endpoint:** `GET /api/partner/franchise/users/search/`

**Query Parameters:**
- search: string (searches email, phone, username)
- exclude_partners: boolean (default: true)
- page: integer (default: 1)
- page_size: integer (default: 20)

**View:**
```python
@franchise_user_router.register(r"partner/franchise/users/search", name="franchise-user-search")
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Search Users",
    description="Search users for vendor creation",
    parameters=[
        OpenApiParameter('search', type=str, description='Search by email, phone, username'),
        OpenApiParameter('exclude_partners', type=bool, description='Exclude existing partners'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class FranchiseUserSearchView(GenericAPIView, BaseAPIView):
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Search users for vendor creation"""
        def operation():
            filters = {
                'search': request.query_params.get('search'),
                'exclude_partners': request.query_params.get('exclude_partners', 'true').lower() == 'true',
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            service = FranchiseUserService()
            return service.search_users_for_vendor(filters)
        
        return self.handle_service_operation(
            operation,
            "Users retrieved successfully",
            "Failed to retrieve users"
        )
```

### 4. Update __init__.py Files
- `api/partners/franchise/services/__init__.py` - Export FranchiseUserService
- `api/partners/franchise/serializers/__init__.py` - Export user serializers
- `api/partners/franchise/views/__init__.py` - Export FranchiseUserSearchView

### 5. Register Router
**Location:** `api/partners/franchise/urls.py`

Add: `franchise_user_router`

## FILES TO CREATE (3 files)
1. `api/partners/franchise/services/franchise_user_service.py` (~80 lines)
2. `api/partners/franchise/serializers/user_serializers.py` (~50 lines)
3. `api/partners/franchise/views/franchise_user_view.py` (~50 lines)

## FILES TO UPDATE (4 files)
1. `api/partners/franchise/services/__init__.py` - Add export
2. `api/partners/franchise/serializers/__init__.py` - Add export
3. `api/partners/franchise/views/__init__.py` - Add export
4. `api/partners/franchise/urls.py` - Register router

## VALIDATION RULES
- Only return active users (is_active=True)
- If exclude_partners=true, exclude users with partner_profile
- Search is case-insensitive
- Return minimal data (no sensitive info like wallet, kyc)

## CONSISTENCY WITH ADMIN
- Same search logic (username, email, phone_number)
- Same pagination approach
- Different response: Minimal fields vs full user data

## TESTING
1. GET /api/partner/franchise/users/search/?search=test
2. GET /api/partner/franchise/users/search/?search=test&exclude_partners=true
3. GET /api/partner/franchise/users/search/?search=test&exclude_partners=false
4. Verify: Only active users returned
5. Verify: Partners excluded when exclude_partners=true

## TOTAL EFFORT
- Lines of code: ~180 lines
- Files: 3 new, 4 updated
- Time estimate: 20 minutes

## READY FOR REVIEW
✅ Plan complete - awaiting approval to implement
