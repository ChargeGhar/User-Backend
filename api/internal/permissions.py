"""
Permission classes for internal IoT action endpoints.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from api.partners.auth.permissions import CanPerformIotAction, IsFranchise
from api.user.auth.permissions import IsStaffPermission


class InternalIoTActionPermission(BasePermission):
    """
    Access policy:
    - Staff: full access
    - Franchise: full IoT access
    - Vendor: all actions except eject (delegated to partner permission rules)
    """

    message = CanPerformIotAction.message

    def has_permission(self, request, view):
        if IsStaffPermission().has_permission(request, view):
            return True
        return CanPerformIotAction().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if IsStaffPermission().has_permission(request, view):
            return True
        return CanPerformIotAction().has_object_permission(request, view, obj)


class InternalIoTEjectPermission(InternalIoTActionPermission):
    """
    Eject access policy:
    - Staff: allowed
    - Franchise: allowed
    - Vendor: denied
    """

    message = IsFranchise.message

    def has_permission(self, request, view):
        if IsStaffPermission().has_permission(request, view):
            return True
        return IsFranchise().has_permission(request, view) and super().has_permission(
            request,
            view,
        )
