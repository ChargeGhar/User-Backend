"""
Admin Advertisement Service
============================
Handles admin-side ad operations: review, approve, reject, schedule, manage.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, QuerySet

from api.common.services.base import BaseService, ServiceException
from api.user.advertisements.models import AdRequest, AdContent, AdDistribution
from api.user.advertisements.repositories import (
    AdRequestRepository,
    AdContentRepository,
    AdDistributionRepository
)
from api.user.stations.models import Station


class AdminAdService(BaseService):
    """Service for admin ad operations"""
    
    def get_ad_requests(self, filters: Optional[Dict[str, Any]] = None) -> QuerySet:
        """
        Get all ad requests with optional filters.
        
        Business Rules:
        1. Return all ads (not filtered by user)
        2. Support filters: status, user_id, search
        3. Search in: title, full_name, user.username, user.email
        4. Return QuerySet for pagination
        5. Include all relations
        
        Args:
            filters: Optional dict with status, user_id, search
            
        Returns:
            QuerySet: Filtered ad requests
        """
        try:
            return AdRequestRepository.get_all_ad_requests(filters)
        except Exception as e:
            self.handle_service_error(e, "Failed to get ad requests")
    
    def get_ad_request_detail(self, ad_id: str) -> AdRequest:
        """
        Get single ad request details for admin.
        
        Business Rules:
        1. No user restriction (admin can see all)
        2. Include all relations
        
        Args:
            ad_id: Ad request ID
            
        Returns:
            AdRequest: Ad request with all relations
            
        Raises:
            ServiceException: If ad not found
        """
        try:
            ad_request = AdRequestRepository.get_by_id(ad_id)
            
            if not ad_request:
                raise ServiceException(
                    detail="Ad request not found",
                    code="ad_not_found"
                )
            
            return ad_request
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to get ad request details")
    
    @transaction.atomic
    def review_ad_request(
        self, ad_id: str, admin_user, validated_data: Dict[str, Any]
    ) -> AdRequest:
        """
        Review ad request and set all details (pricing, stations, content settings).
        
        Business Rules:
        1. Valid statuses: SUBMITTED, UNDER_REVIEW
        2. Set status to UNDER_REVIEW
        3. Update: title, description, duration_days, admin_price, admin_notes, start_date
        4. Update AdContent: duration_seconds, display_order
        5. Clear and recreate AdDistribution records
        6. Validate all stations exist
        7. Set reviewed_by and reviewed_at
        8. Use row-level locking
        
        Args:
            ad_id: Ad request ID
            admin_user: Admin performing review
            validated_data: Dict with all review fields
            
        Returns:
            AdRequest: Updated ad request
            
        Raises:
            ServiceException: If validation fails
        """
        try:
            # Get ad request with row-level lock
            ad_request = AdRequest.objects.select_for_update().get(id=ad_id)
            
            # Validate status
            if ad_request.status not in ['SUBMITTED', 'UNDER_REVIEW']:
                raise ServiceException(
                    detail=f"Cannot review ad in {ad_request.status} status. "
                           f"Only SUBMITTED or UNDER_REVIEW ads can be reviewed.",
                    code="invalid_status"
                )
            
            # Validate stations exist
            station_ids = validated_data['station_ids']
            stations = Station.objects.filter(id__in=station_ids)
            if stations.count() != len(station_ids):
                found_ids = set(str(s.id) for s in stations)
                missing_ids = set(str(sid) for sid in station_ids) - found_ids
                raise ServiceException(
                    detail=f"Stations not found: {', '.join(missing_ids)}",
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
            
            # Calculate end_date if start_date provided
            if ad_request.start_date and ad_request.duration_days:
                ad_request.end_date = ad_request.start_date + timedelta(
                    days=ad_request.duration_days
                )
            
            ad_request.save()
            
            # Update AdContent
            ad_content = AdContentRepository.get_by_ad_request(ad_request.id)
            if ad_content:
                AdContentRepository.update(
                    ad_content,
                    duration_seconds=validated_data.get('duration_seconds', 5),
                    display_order=validated_data.get('display_order', 0)
                )
                
                # Clear and recreate AdDistribution records
                AdDistributionRepository.delete_by_ad_content(ad_content.id)
                
                for station_id in station_ids:
                    station = stations.get(id=station_id)
                    AdDistributionRepository.create(
                        ad_content=ad_content,
                        station=station
                    )
            
            self.log_info(
                f"Ad request reviewed: {ad_request.id} by admin {admin_user.username}. "
                f"Price: NPR {ad_request.admin_price}, Stations: {len(station_ids)}"
            )
            
            return ad_request
            
        except AdRequest.DoesNotExist:
            raise ServiceException(
                detail="Ad request not found",
                code="ad_not_found"
            )
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to review ad request")
    
    @transaction.atomic
    def perform_ad_action(
        self, ad_id: str, admin_user, action: str, data: Dict[str, Any]
    ) -> AdRequest:
        """
        Perform action on ad request (approve, reject, schedule, pause, resume, cancel, complete).
        
        Business Rules:
        - APPROVE: UNDER_REVIEW → APPROVED → PENDING_PAYMENT (if price set)
        - REJECT: SUBMITTED/UNDER_REVIEW → REJECTED (requires rejection_reason)
        - SCHEDULE: PAID → SCHEDULED (requires start_date, calculates end_date)
        - PAUSE: RUNNING → PAUSED
        - RESUME: PAUSED → RUNNING
        - CANCEL: Any except COMPLETED → CANCELLED
        - COMPLETE: RUNNING → COMPLETED (sets completed_at)
        
        Args:
            ad_id: Ad request ID
            admin_user: Admin performing action
            action: Action to perform
            data: Action-specific data
            
        Returns:
            AdRequest: Updated ad request
            
        Raises:
            ServiceException: If validation fails
        """
        try:
            # Get ad request with row-level lock
            ad_request = AdRequest.objects.select_for_update().get(id=ad_id)
            
            # Route to specific action handler
            if action == 'approve':
                return self._approve_ad(ad_request, admin_user)
            elif action == 'reject':
                return self._reject_ad(ad_request, admin_user, data.get('rejection_reason', ''))
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
        except ServiceException:
            raise
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
            self.log_info(f"Ad approved and set to PENDING_PAYMENT: {ad_request.id}")
        else:
            self.log_info(f"Ad approved: {ad_request.id}")
        
        return ad_request
    
    def _reject_ad(self, ad_request: AdRequest, admin_user, reason: str) -> AdRequest:
        """Reject ad request"""
        if ad_request.status not in ['SUBMITTED', 'UNDER_REVIEW']:
            raise ServiceException(
                detail="Only submitted or under review ads can be rejected",
                code="invalid_status"
            )
        
        if not reason:
            raise ServiceException(
                detail="Rejection reason is required",
                code="rejection_reason_required"
            )
        
        ad_request.status = 'REJECTED'
        ad_request.rejection_reason = reason
        ad_request.reviewed_by = admin_user
        ad_request.reviewed_at = timezone.now()
        ad_request.save()
        
        self.log_info(f"Ad rejected: {ad_request.id}. Reason: {reason[:50]}")
        return ad_request
    
    def _schedule_ad(self, ad_request: AdRequest, data: Dict[str, Any]) -> AdRequest:
        """Schedule ad to run"""
        if ad_request.status != 'PAID':
            raise ServiceException(
                detail="Only paid ads can be scheduled",
                code="invalid_status"
            )
        
        start_date = data.get('start_date')
        if not start_date:
            raise ServiceException(
                detail="Start date is required for scheduling",
                code="start_date_required"
            )
        
        end_date = data.get('end_date')
        if not end_date and ad_request.duration_days:
            end_date = start_date + timedelta(days=ad_request.duration_days)
        
        ad_request.start_date = start_date
        ad_request.end_date = end_date
        ad_request.status = 'SCHEDULED'
        ad_request.save()
        
        self.log_info(
            f"Ad scheduled: {ad_request.id}. "
            f"Start: {start_date}, End: {end_date}"
        )
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
            if ad_request.admin_notes:
                ad_request.admin_notes += f"\nCancellation reason: {reason}"
            else:
                ad_request.admin_notes = f"Cancellation reason: {reason}"
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
    def update_schedule(
        self, ad_id: str, validated_data: Dict[str, Any]
    ) -> AdRequest:
        """
        Update ad schedule (start_date and/or end_date).
        
        Business Rules:
        1. Valid statuses: SCHEDULED, RUNNING, PAUSED
        2. At least one of start_date or end_date must be provided
        3. Use row-level locking
        
        Args:
            ad_id: Ad request ID
            validated_data: Dict with start_date and/or end_date
            
        Returns:
            AdRequest: Updated ad request
            
        Raises:
            ServiceException: If validation fails
        """
        try:
            # Get ad request with row-level lock
            ad_request = AdRequest.objects.select_for_update().get(id=ad_id)
            
            # Validate status
            if ad_request.status not in ['SCHEDULED', 'RUNNING', 'PAUSED']:
                raise ServiceException(
                    detail="Can only update schedule for scheduled/running/paused ads",
                    code="invalid_status"
                )
            
            # Update dates
            if validated_data.get('start_date'):
                ad_request.start_date = validated_data['start_date']
            
            if validated_data.get('end_date'):
                ad_request.end_date = validated_data['end_date']
            
            ad_request.save()
            
            self.log_info(
                f"Ad schedule updated: {ad_request.id}. "
                f"Start: {ad_request.start_date}, End: {ad_request.end_date}"
            )
            
            return ad_request
            
        except AdRequest.DoesNotExist:
            raise ServiceException(
                detail="Ad request not found",
                code="ad_not_found"
            )
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to update schedule")
