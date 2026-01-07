"""
Service for admin profile management
============================================================

This module contains service classes for admin profile management,
including authentication, profile CRUD, and role management.

Created: 2025-11-05
"""
from __future__ import annotations
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from api.common.services.base import CRUDService, ServiceException
from api.admin.models import AdminProfile, AdminActionLog
from api.users.models import User, UserProfile
from api.points.models import UserPoints
from api.payments.models import Wallet


class AdminProfileService(CRUDService):
    """Service for admin profile management"""
    model = AdminProfile
    
    def authenticate_admin(self, email: str, password: str, request=None) -> Dict[str, Any]:
        """
        Authenticate admin user and generate JWT tokens
        
        Args:
            email: Admin email
            password: Admin password
            request: HTTP request object for audit logging
            
        Returns:
            Dict with user info, tokens, and admin profile
            
        Raises:
            ServiceException: If authentication fails
        """
        try:
            user = User.objects.get(email=email, is_staff=True, is_active=True)
        except User.DoesNotExist:
            raise ServiceException(
                detail="Admin user not found or inactive",
                code="admin_not_found"
            )
        
        # Verify password
        if not user.check_password(password):
            raise ServiceException(
                detail="Invalid password",
                code="invalid_password"
            )
        
        # Ensure all required objects exist (backward compatibility)
        self._ensure_admin_objects(user)
        
        # Get admin profile and check if active
        admin_profile = user.admin_profile
        if not admin_profile.is_active:
            raise ServiceException(
                detail="Admin profile is deactivated",
                code="admin_deactivated"
            )
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Log authentication
        if request:
            from api.users.services.account_service import AccountService
            account_service = AccountService()
            account_service.log_auth_action(user, 'LOGIN', request)
        
        self.log_info(f"Admin logged in: {user.email}")
        
        return {
            'user_id': str(user.id),
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'role': admin_profile.role,
            },
            'message': 'Admin login successful'
        }
    
    def _ensure_admin_objects(self, user: User) -> None:
        """Ensure admin user has all required related objects"""
        UserProfile.objects.get_or_create(
            user=user, 
            defaults={'is_profile_complete': False}
        )
        UserPoints.objects.get_or_create(
            user=user, 
            defaults={'current_points': 0, 'total_points': 0}
        )
        Wallet.objects.get_or_create(
            user=user, 
            defaults={'balance': 0, 'currency': 'NPR', 'is_active': True}
        )
        AdminProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'super_admin' if user.is_superuser else 'admin',
                'created_by': user,
                'is_active': True
            }
        )
    
    def get_admin_profiles(self) -> list:
        """Get all admin profiles"""
        return AdminProfile.objects.select_related('user', 'created_by').all()
    
    def get_admin_profile(self, profile_id: str) -> AdminProfile:
        """Get specific admin profile by ID"""
        try:
            return AdminProfile.objects.select_related('user', 'created_by').get(id=profile_id)
        except AdminProfile.DoesNotExist:
            raise ServiceException(
                detail="Admin profile not found",
                code="profile_not_found"
            )
    
    def get_current_admin_profile(self, user: User) -> Dict[str, Any]:
        """Get current admin's profile with permissions"""
        try:
            admin_profile = user.admin_profile
        except AttributeError:
            raise ServiceException(
                detail="Admin profile not found",
                code="profile_not_found"
            )
        
        return {
            'user_id': str(user.id),
            'email': user.email,
            'username': user.username,
            'role': admin_profile.role,
            'is_active': admin_profile.is_active,
            'is_super_admin': admin_profile.is_super_admin,
            'created_at': admin_profile.created_at,
            'permissions': self._get_permissions(admin_profile)
        }
    
    def _get_permissions(self, admin_profile: AdminProfile) -> Dict[str, bool]:
        """Get permissions based on admin role"""
        return {
            'can_manage_users': admin_profile.role in ['super_admin', 'admin'],
            'can_manage_stations': admin_profile.role in ['super_admin', 'admin'],
            'can_manage_content': True,
            'can_view_analytics': True,
            'can_manage_finances': admin_profile.role == 'super_admin',
            'can_manage_admins': admin_profile.role == 'super_admin',
        }
    
    @transaction.atomic
    def create_admin_profile(
        self, 
        user_id: str, 
        role: str, 
        created_by: User,
        password: str = None,
        request=None
    ) -> AdminProfile:
        """
        Create new admin profile
        
        Args:
            user_id: User ID to create admin profile for
            role: Admin role (super_admin, admin, moderator)
            created_by: User creating the profile
            password: Password for the admin user (required)
            request: HTTP request for audit logging
            
        Returns:
            Created AdminProfile
            
        Raises:
            ServiceException: If validation fails
        """
        # Permission check
        if created_by.admin_profile.role != 'super_admin':
            raise ServiceException(
                detail="Only super admin can create admin profiles",
                code="permission_denied"
            )
        
        # Validate password provided
        if not password:
            raise ServiceException(
                detail="Password is required when creating admin profile",
                code="password_required"
            )
        
        # Validate user exists (super admin can promote any user)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ServiceException(
                detail="User not found",
                code="user_not_found"
            )
        
        # Check for duplicate
        if AdminProfile.objects.filter(user=user).exists():
            raise ServiceException(
                detail="Admin profile already exists for this user",
                code="profile_exists"
            )
        
        # Only super admin can create super admin
        if role == 'super_admin' and created_by.admin_profile.role != 'super_admin':
            raise ServiceException(
                detail="Only super admin can create super admin profiles",
                code="permission_denied"
            )
        
        # Set staff status FIRST (required for set_password to work)
        # The User model's set_password() only works when is_staff=True
        user.is_staff = True
        if role == 'super_admin':
            user.is_superuser = True
        
        # NOW set password (after is_staff=True)
        user.set_password(password)
        
        # Ensure required objects exist (UserProfile, UserPoints, Wallet)
        try:
            UserProfile.objects.get_or_create(
                user=user, 
                defaults={'is_profile_complete': False}
            )
        except Exception:
            pass
            
        try:
            UserPoints.objects.get_or_create(
                user=user, 
                defaults={'current_points': 0, 'total_points': 0}
            )
        except Exception:
            pass
            
        try:
            Wallet.objects.get_or_create(
                user=user, 
                defaults={'balance': 0, 'currency': 'NPR', 'is_active': True}
            )
        except Exception:
            pass
        
        # Save user with password and staff status
        user.save()
        
        # Create profile
        profile = AdminProfile.objects.create(
            user=user,
            role=role,
            created_by=created_by
        )
        
        # Log action
        self._log_admin_action(
            admin_user=created_by,
            action_type='CREATE_ADMIN',
            target_model='AdminProfile',
            target_id=str(profile.id),
            changes={'role': role, 'user_email': user.email},
            description=f"Created {role} profile for {user.email}",
            request=request
        )
        
        self.log_info(f"Admin profile created: {user.email} as {role}")
        return profile
    
    @transaction.atomic
    def update_admin_role(
        self, 
        profile_id: str, 
        new_role: str, 
        changed_by: User,
        request=None
    ) -> AdminProfile:
        """
        Update admin profile role
        
        Args:
            profile_id: Profile ID to update
            new_role: New role to assign
            changed_by: User making the change
            request: HTTP request for audit logging
            
        Returns:
            Updated AdminProfile
            
        Raises:
            ServiceException: If validation fails
        """
        profile = self.get_admin_profile(profile_id)
        
        # Can't change own role
        if profile.user.id == changed_by.id:
            raise ServiceException(
                detail="Cannot change your own role",
                code="cannot_change_own_role"
            )
        
        # Validate role change
        can_change, reason = profile.can_change_role(new_role, changed_by.admin_profile)
        if not can_change:
            raise ServiceException(detail=reason, code="role_change_not_allowed")
        
        # Update role
        old_role = profile.role
        profile.role = new_role
        profile.save(update_fields=['role', 'updated_at'])
        
        # Log action
        self._log_admin_action(
            admin_user=changed_by,
            action_type='UPDATE_ADMIN_ROLE',
            target_model='AdminProfile',
            target_id=str(profile.id),
            changes={'old_role': old_role, 'new_role': new_role, 'user_email': profile.user.email},
            description=f"Changed {profile.user.email} role from {old_role} to {new_role}",
            request=request
        )
        
        self.log_info(f"Admin role updated: {profile.user.email} {old_role} -> {new_role}")
        return profile
    
    @transaction.atomic
    def update_admin_profile(
        self,
        profile_id: str,
        changed_by: User,
        new_role: str = None,
        new_password: str = None,
        is_active: bool = None,
        reason: str = None,
        request=None
    ) -> AdminProfile:
        """
        Update admin profile - unified method for role, password, and status updates
        
        Args:
            profile_id: Admin profile ID
            changed_by: User making the change
            new_role: New role (optional)
            new_password: New password (optional)
            is_active: Activate/deactivate (optional)
            reason: Reason for changes (optional)
            request: HTTP request for audit logging
            
        Returns:
            Updated AdminProfile
            
        Raises:
            ServiceException: If validation fails
        """
        # Update role if provided
        if new_role is not None:
            self.update_admin_role(
                profile_id=profile_id,
                new_role=new_role,
                changed_by=changed_by,
                request=request
            )
        
        # Update password if provided
        if new_password is not None:
            self.update_admin_password(
                profile_id=profile_id,
                new_password=new_password,
                changed_by=changed_by,
                request=request
            )
        
        # Update active status if provided
        if is_active is not None:
            if is_active:
                self.activate_admin(
                    profile_id=profile_id,
                    reason=reason or '',
                    activated_by=changed_by,
                    request=request
                )
            else:
                self.deactivate_admin(
                    profile_id=profile_id,
                    reason=reason or '',
                    deactivated_by=changed_by,
                    request=request
                )
        
        # Return updated profile
        return self.get_admin_profile(profile_id)
    
    @transaction.atomic
    def update_admin_password(
        self,
        profile_id: str,
        new_password: str,
        changed_by: User,
        request=None
    ) -> Dict[str, str]:
        """
        Update admin user's password
        
        Args:
            profile_id: Admin profile ID
            new_password: New password to set
            changed_by: User making the change (must be super admin or self)
            request: HTTP request for audit logging
            
        Returns:
            Success message dict
            
        Raises:
            ServiceException: If validation fails
        """
        profile = self.get_admin_profile(profile_id)
        
        # Permission check: Super admin can change any password, others can only change their own
        if changed_by.admin_profile.role != 'super_admin' and profile.user.id != changed_by.id:
            raise ServiceException(
                detail="You can only change your own password",
                code="permission_denied"
            )
        
        # Update password
        user = profile.user
        user.set_password(new_password)
        user.save(update_fields=['password'])
        
        # Log action
        self._log_admin_action(
            admin_user=changed_by,
            action_type='UPDATE_ADMIN_PASSWORD',
            target_model='User',
            target_id=str(user.id),
            changes={'user_email': user.email},
            description=f"Password updated for {user.email}",
            request=request
        )
        
        self.log_info(f"Admin password updated: {user.email}")
        return {"message": "Password updated successfully"}
    
    @transaction.atomic
    def deactivate_admin(
        self, 
        profile_id: str, 
        reason: str, 
        deactivated_by: User,
        request=None
    ) -> Dict[str, str]:
        """
        Deactivate admin profile
        
        Args:
            profile_id: Profile ID to deactivate
            reason: Reason for deactivation
            deactivated_by: User performing deactivation
            request: HTTP request for audit logging
            
        Returns:
            Success message dict
            
        Raises:
            ServiceException: If validation fails
        """
        profile = self.get_admin_profile(profile_id)
        
        # Can't deactivate self
        if profile.user.id == deactivated_by.id:
            raise ServiceException(
                detail="Cannot deactivate your own account",
                code="cannot_deactivate_self"
            )
        
        # Validate can be deactivated
        can_deactivate, validation_reason = profile.can_be_deactivated()
        if not can_deactivate:
            raise ServiceException(detail=validation_reason, code="deactivation_not_allowed")
        
        # Deactivate
        profile.is_active = False
        profile.save(update_fields=['is_active', 'updated_at'])
        
        # Log action
        self._log_admin_action(
            admin_user=deactivated_by,
            action_type='DEACTIVATE_ADMIN',
            target_model='AdminProfile',
            target_id=str(profile.id),
            changes={'is_active': False, 'user_email': profile.user.email, 'reason': reason},
            description=f"Deactivated admin {profile.user.email}. Reason: {reason}",
            request=request
        )
        
        self.log_info(f"Admin deactivated: {profile.user.email}")
        return {'message': 'Admin profile deactivated successfully'}
    
    @transaction.atomic
    def activate_admin(
        self, 
        profile_id: str, 
        reason: str, 
        activated_by: User,
        request=None
    ) -> Dict[str, str]:
        """
        Activate admin profile
        
        Args:
            profile_id: Profile ID to activate
            reason: Reason for activation
            activated_by: User performing activation
            request: HTTP request for audit logging
            
        Returns:
            Success message dict
        """
        profile = self.get_admin_profile(profile_id)
        
        # Activate
        profile.is_active = True
        profile.save(update_fields=['is_active', 'updated_at'])
        
        # Log action
        self._log_admin_action(
            admin_user=activated_by,
            action_type='ACTIVATE_ADMIN',
            target_model='AdminProfile',
            target_id=str(profile.id),
            changes={'is_active': True, 'user_email': profile.user.email, 'reason': reason},
            description=f"Activated admin {profile.user.email}. Reason: {reason}",
            request=request
        )
        
        self.log_info(f"Admin activated: {profile.user.email}")
        return {'message': 'Admin profile activated successfully'}
    
    def _log_admin_action(
        self, 
        admin_user: User, 
        action_type: str, 
        target_model: str, 
        target_id: str, 
        changes: Dict[str, Any], 
        description: str = "",
        request=None
    ) -> None:
        """Log admin action for audit trail"""
        try:
            ip_address = request.META.get('REMOTE_ADDR', '') if request else ''
            user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
            
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type=action_type,
                target_model=target_model,
                target_id=target_id,
                changes=changes,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            self.log_error(f"Failed to log admin action: {str(e)}")
