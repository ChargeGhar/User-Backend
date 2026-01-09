"""
Service for admin station amenity management
============================================================

This module contains service classes for managing station amenities.
"""
from __future__ import annotations
from typing import Dict, Any
from django.db import transaction
from django.db.models import Q, Count
from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.user.stations.models import StationAmenity


class AdminAmenityService(CRUDService):
    """Service for admin station amenity management"""
    model = StationAmenity
    
    def get_amenities_list(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get paginated list of amenities with filters"""
        try:
            queryset = StationAmenity.objects.all()
            
            # Apply filters
            if filters:
                if filters.get('is_active') is not None:
                    queryset = queryset.filter(is_active=filters['is_active'])
                
                if filters.get('search'):
                    search_term = filters['search']
                    queryset = queryset.filter(
                        Q(name__icontains=search_term) |
                        Q(description__icontains=search_term)
                    )
            
            # Order by name
            queryset = queryset.order_by('name')
            
            # Pagination
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20
            
            return paginate_queryset(queryset, page, page_size)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get amenities list")
    
    def get_amenity_detail(self, amenity_id: str) -> StationAmenity:
        """
        Get detailed amenity information
        
        Args:
            amenity_id: Amenity UUID
            
        Returns:
            StationAmenity instance
        """
        try:
            amenity = StationAmenity.objects.annotate(
                stations_count=Count('stationamenitymapping')
            ).get(id=amenity_id)
            
            return amenity
            
        except StationAmenity.DoesNotExist:
            raise ServiceException(
                detail="Amenity not found",
                code="amenity_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get amenity detail")
    
    def create_amenity(
        self,
        amenity_data: Dict[str, Any],
        admin_user = None,
        request = None
    ) -> StationAmenity:
        """
        Create a new station amenity
        
        Args:
            amenity_data: Amenity information
            admin_user: Admin user creating the amenity
            request: HTTP request for logging
            
        Returns:
            Created StationAmenity instance
        """
        try:
            # Create amenity
            amenity = StationAmenity.objects.create(**amenity_data)
            
            self.log_info(f"Amenity created successfully: {amenity.name}")
            
            # Log admin action after creation
            if admin_user:
                self._log_admin_action(
                    admin_user=admin_user,
                    action_type='CREATE_AMENITY',
                    target_model='StationAmenity',
                    target_id=str(amenity.id),
                    changes=amenity_data,
                    description=f"Created new amenity: {amenity.name}",
                    request=request
                )
            
            return amenity
            
        except Exception as e:
            self.handle_service_error(e, "Failed to create amenity")
    
    def update_amenity(
        self,
        amenity_id: str,
        update_data: Dict[str, Any],
        admin_user = None,
        request = None
    ) -> StationAmenity:
        """
        Update amenity details
        
        Args:
            amenity_id: Amenity UUID
            update_data: Fields to update
            admin_user: Admin user performing update
            request: HTTP request for logging
            
        Returns:
            Updated StationAmenity instance
        """
        try:
            amenity = StationAmenity.objects.get(id=amenity_id)
            
            # Track changes for logging
            changes = {}
            for field, value in update_data.items():
                old_value = getattr(amenity, field)
                if old_value != value:
                    changes[field] = {
                        'old': str(old_value),
                        'new': str(value)
                    }
                    setattr(amenity, field, value)
            
            if changes:
                amenity.save()
                
                self.log_info(f"Amenity updated successfully: {amenity.name}")
                
                # Log admin action after save completes
                if admin_user:
                    self._log_admin_action(
                        admin_user=admin_user,
                        action_type='UPDATE_AMENITY',
                        target_model='StationAmenity',
                        target_id=str(amenity.id),
                        changes=changes,
                        description=f"Updated amenity: {amenity.name}",
                        request=request
                    )
            
            return amenity
            
        except StationAmenity.DoesNotExist:
            raise ServiceException(
                detail="Amenity not found",
                code="amenity_not_found"
            )
    
    @transaction.atomic
    def delete_amenity(
        self,
        amenity_id: str,
        admin_user = None,
        request = None
    ) -> Dict[str, str]:
        """
        Delete a station amenity (only if not assigned to any stations)
        
        Args:
            amenity_id: Amenity UUID
            admin_user: Admin user performing deletion
            request: HTTP request for logging
            
        Returns:
            Success message dict
        """
        try:
            from api.user.stations.models import StationAmenityMapping
            
            amenity = StationAmenity.objects.get(id=amenity_id)
            
            # Check if amenity is assigned to any stations
            assigned_count = StationAmenityMapping.objects.filter(
                amenity=amenity
            ).count()
            
            if assigned_count > 0:
                raise ServiceException(
                    detail=f"Cannot delete amenity assigned to {assigned_count} station(s). Remove from stations first.",
                    code="amenity_in_use"
                )
            
            # Hard delete (since no stations are using it)
            amenity_name = amenity.name
            amenity.delete()
            
            self.log_info(f"Amenity deleted successfully: {amenity_name}")
            
            # Log admin action AFTER transaction commits
            if admin_user:
                transaction.on_commit(
                    lambda: self._log_admin_action(
                        admin_user=admin_user,
                        action_type='DELETE_AMENITY',
                        target_model='StationAmenity',
                        target_id=str(amenity_id),
                        changes={'name': amenity_name},
                        description=f"Deleted amenity: {amenity_name}",
                        request=request
                    )
                )
            
            return {'message': 'Amenity deleted successfully'}
            
        except StationAmenity.DoesNotExist:
            raise ServiceException(
                detail="Amenity not found",
                code="amenity_not_found"
            )
    
    def _log_admin_action(
        self,
        admin_user,
        action_type: str,
        target_model: str,
        target_id: str,
        changes: dict,
        description: str,
        request=None
    ):
        """Log admin action to audit trail"""
        try:
            from api.admin.models import AdminActionLog
            
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type=action_type,
                target_model=target_model,
                target_id=target_id,
                changes=changes,
                description=description,
                ip_address=self._get_client_ip(request) if request else '',
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
            )
        except Exception as e:
            self.log_error(f"Failed to log admin action: {str(e)}")
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
