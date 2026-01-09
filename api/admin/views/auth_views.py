"""
Admin authentication and profile management - handles admin login and profile CRUD operations
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers
from api.admin.services import AdminProfileService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.common.services.base import ServiceException
from api.user.auth.permissions import IsStaffPermission

auth_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@auth_router.register(r"admin/login", name="admin-login")
@extend_schema(
    tags=["Admin - Auth"],
    summary="Admin Login",
    description="Password-based login for admin users (generates JWT tokens)",
    request=serializers.AdminLoginSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminLoginView(GenericAPIView, BaseAPIView):
    """Admin login endpoint - generates JWT tokens using the same system as regular auth"""
    serializer_class = serializers.AdminLoginSerializer
    permission_classes = [AllowAny]
    
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        """Admin login with email/password - generates tokens via AdminProfileService"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Use service for authentication
            service = AdminProfileService()
            result = service.authenticate_admin(email, password, request)
            
            logger.info(f"Admin logged in successfully: {email}")
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="Admin login successful",
            error_message="Admin login failed"
        )


# ============================================================
# Admin Profile Management Views
# ============================================================
@auth_router.register(r"admin/profiles", name="admin-profiles")
@extend_schema(
    tags=["Admin - Auth"],
    summary="Admin Profile Management",
    description="Manage admin profiles and roles (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminProfileView(GenericAPIView, BaseAPIView):
    """Admin profile management"""
    serializer_class = serializers.AdminProfileSerializer
    permission_classes = [IsStaffPermission]

    @extend_schema(
        summary="List Admin Profiles",
        description="Get list of all admin profiles"
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get admin profile list"""
        def operation():
            service = AdminProfileService()
            profiles = service.get_admin_profiles()
            serializer = self.get_serializer(profiles, many=True)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Admin profiles retrieved successfully",
            "Failed to retrieve admin profiles"
        )

    @extend_schema(
        summary="Create Admin Profile",
        description="Create a new admin profile (Super Admin only)",
        request=serializers.AdminProfileCreateSerializer
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create admin profile"""
        def operation():
            create_serializer = serializers.AdminProfileCreateSerializer(data=request.data)
            create_serializer.is_valid(raise_exception=True)
            
            user_id = create_serializer.validated_data['user']
            role = create_serializer.validated_data['role']
            password = create_serializer.validated_data['password']
            
            # Use service to create profile
            service = AdminProfileService()
            profile = service.create_admin_profile(
                user_id=user_id,
                role=role,
                password=password,
                created_by=request.user,
                request=request
            )
            
            response_serializer = self.get_serializer(profile)
            return response_serializer.data
        
        result = self.handle_service_operation(
            operation,
            "Admin profile created successfully",
            "Failed to create admin profile"
        )
        result.status_code = status.HTTP_201_CREATED
        return result


# ============================================================
# Current Admin Profile View
# ============================================================
@auth_router.register(r"admin/me", name="admin-me")
@extend_schema(
    tags=["Admin - Auth"],
    summary="Get Current Admin Profile",
    description="Get the logged-in admin's profile with permissions",
    responses={200: BaseResponseSerializer}
)
class AdminMeView(GenericAPIView, BaseAPIView):
    """Current admin profile endpoint"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get current admin's profile with permissions"""
        def operation():
            service = AdminProfileService()
            return service.get_current_admin_profile(request.user)
        
        return self.handle_service_operation(
            operation,
            "Admin profile retrieved successfully",
            "Failed to retrieve admin profile"
        )


# ============================================================
# Admin Profile Detail View
# ============================================================
@auth_router.register(r"admin/profiles/<uuid:profile_id>", name="admin-profile-detail")
@extend_schema(
    tags=["Admin - Auth"],
    summary="Admin Profile Details",
    description="Get, update, or deactivate a specific admin profile",
    responses={200: BaseResponseSerializer}
)
class AdminProfileDetailView(GenericAPIView, BaseAPIView):
    """Admin profile detail operations"""
    serializer_class = serializers.AdminProfileSerializer
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="Get Admin Profile",
        description="Get a specific admin profile by ID"
    )
    @log_api_call()
    def get(self, request: Request, profile_id: str) -> Response:
        """Get specific admin profile"""
        def operation():
            service = AdminProfileService()
            profile = service.get_admin_profile(profile_id)
            serializer = self.get_serializer(profile)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Admin profile retrieved successfully",
            "Failed to retrieve admin profile"
        )
    
    @extend_schema(
        summary="Update Admin Profile",
        description="Update admin's role, password, or active status. Super admin can update any admin, others can only update their own password.",
        request=serializers.AdminProfileUpdateSerializer
    )
    @log_api_call()
    def patch(self, request: Request, profile_id: str) -> Response:
        """Update admin profile (role, password, is_active)"""
        def operation():
            # Validate request
            update_serializer = serializers.AdminProfileUpdateSerializer(data=request.data)
            update_serializer.is_valid(raise_exception=True)
            
            # Use unified service method
            service = AdminProfileService()
            profile = service.update_admin_profile(
                profile_id=profile_id,
                changed_by=request.user,
                new_role=update_serializer.validated_data.get('role'),
                new_password=update_serializer.validated_data.get('new_password'),
                is_active=update_serializer.validated_data.get('is_active'),
                reason=update_serializer.validated_data.get('reason'),
                request=request
            )
            
            serializer = self.get_serializer(profile)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Admin profile updated successfully",
            "Failed to update admin profile"
        )
    
    @extend_schema(
        summary="Delete Admin Profile",
        description="Delete an admin profile (Super Admin only)"
    )
    @log_api_call()
    def delete(self, request: Request, profile_id: str) -> Response:
        """Delete admin profile"""
        def operation():
            # Only super admin can delete
            if request.user.admin_profile.role != 'super_admin':
                raise ServiceException(
                    detail="Only super admin can delete admin profiles",
                    code="permission_denied"
                )
            
            service = AdminProfileService()
            profile = service.get_admin_profile(profile_id)
            
            # Can't delete own profile
            if profile.user.id == request.user.id:
                raise ServiceException(
                    detail="Cannot delete your own profile",
                    code="cannot_delete_self"
                )
            
            # Deactivate instead of hard delete
            return service.deactivate_admin(
                profile_id=profile_id,
                reason="Profile deleted",
                deactivated_by=request.user,
                request=request
            )
        
        return self.handle_service_operation(
            operation,
            "Admin profile deleted successfully",
            "Failed to delete admin profile"
        )