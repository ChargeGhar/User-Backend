from __future__ import annotations

from typing import Any, cast

from rest_framework import permissions
from rest_framework.request import Request


class IsStaffPermission(permissions.BasePermission):
    """Permission class for admin staff users"""
    def has_permission(self, request: Request, view: Any) -> bool:  # noqa: ARG002
        return cast(bool, request.user.is_staff)


class IsSuperAdminPermission(permissions.BasePermission):
    """Permission class for super admin users only"""
    def has_permission(self, request: Request, view: Any) -> bool:  # noqa: ARG002
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not request.user.is_staff:
            return False
        
        try:
            return request.user.admin_profile.role == 'super_admin'
        except:
            return False
