"""
Admin Rental Service
============================================================

This module contains service classes for admin rental issue management operations.

Created: 2025-11-06
"""

from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from api.common.services.base import BaseService, ServiceException
from api.user.rentals.models import Rental, RentalIssue

User = get_user_model()


class AdminRentalService(BaseService):
    """Service for admin rental issue management"""
    
    def get_rental_issues(
        self,
        status: str = None,
        issue_type: str = None,
        search: str = None,
        ordering: str = '-reported_at'
    ):
        """
        Get list of rental issues with filtering
        
        Args:
            status: Filter by status (REPORTED, RESOLVED)
            issue_type: Filter by issue type
            search: Search in description or rental code
            ordering: Order by field
            
        Returns:
            Queryset of rental issues
        """
        queryset = RentalIssue.objects.select_related(
            'rental__user',
            'rental__power_bank',
            'rental__station',
            'rental__return_station'
        )
        
        # Apply filters
        if status:
            queryset = queryset.filter(status=status)
        
        if issue_type:
            queryset = queryset.filter(issue_type=issue_type)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(rental__rental_code__icontains=search)
            )
        
        # Apply ordering
        queryset = queryset.order_by(ordering)
        
        return queryset
    
    def get_rental_issue(self, issue_id: str) -> RentalIssue:
        """
        Get specific rental issue by ID
        
        Args:
            issue_id: Issue ID
            
        Returns:
            RentalIssue instance
            
        Raises:
            ServiceException: If issue not found
        """
        try:
            return RentalIssue.objects.select_related(
                'rental__user',
                'rental__power_bank',
                'rental__station',
                'rental__return_station'
            ).get(id=issue_id)
        except RentalIssue.DoesNotExist:
            raise ServiceException(
                detail="Rental issue not found",
                code="rental_issue_not_found"
            )
    
    @transaction.atomic
    def update_rental_issue_status(
        self,
        issue_id: str,
        status: str,
        admin_user: User,
        notes: str = None,
        request=None
    ) -> RentalIssue:
        """
        Update rental issue status
        
        Args:
            issue_id: Issue ID
            status: New status (REPORTED, RESOLVED)
            admin_user: Admin user making the update
            notes: Optional admin notes
            request: HTTP request for audit logging
            
        Returns:
            Updated RentalIssue instance
            
        Raises:
            ServiceException: If validation fails
        """
        issue = self.get_rental_issue(issue_id)
        
        # Validate status
        valid_statuses = ['REPORTED', 'RESOLVED']
        if status not in valid_statuses:
            raise ServiceException(
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                code="invalid_status"
            )
        
        # Update status
        old_status = issue.status
        issue.status = status
        
        # Set resolved_at if resolved
        if status == 'RESOLVED' and old_status != 'RESOLVED':
            issue.resolved_at = timezone.now()
        
        issue.save(update_fields=['status', 'resolved_at', 'updated_at'])
        
        # Log admin action
        self._log_admin_action(
            admin_user=admin_user,
            action_type='UPDATE_RENTAL_ISSUE_STATUS',
            target_model='RentalIssue',
            target_id=str(issue.id),
            changes={
                'old_status': old_status,
                'new_status': status,
                'rental_code': issue.rental.rental_code,
                'notes': notes
            },
            description=f"Updated rental issue {issue.id} status from {old_status} to {status}",
            request=request
        )
        
        self.log_info(f"Rental issue {issue.id} status updated: {old_status} -> {status}")
        
        # Send notification to user if resolved
        if status == 'RESOLVED':
            self._send_issue_resolved_notification(issue)
        
        return issue
    
    @transaction.atomic
    def delete_rental_issue(
        self,
        issue_id: str,
        admin_user: User,
        request=None
    ) -> Dict[str, str]:
        """
        Delete rental issue (soft delete by marking as resolved)
        
        Args:
            issue_id: Issue ID
            admin_user: Admin user making the deletion
            request: HTTP request for audit logging
            
        Returns:
            Success message dict
            
        Raises:
            ServiceException: If validation fails
        """
        issue = self.get_rental_issue(issue_id)
        
        # Soft delete by marking as resolved
        if issue.status != 'RESOLVED':
            issue.status = 'RESOLVED'
            issue.resolved_at = timezone.now()
            issue.save(update_fields=['status', 'resolved_at', 'updated_at'])
        
        # Log admin action
        self._log_admin_action(
            admin_user=admin_user,
            action_type='DELETE_RENTAL_ISSUE',
            target_model='RentalIssue',
            target_id=str(issue.id),
            changes={
                'rental_code': issue.rental.rental_code,
                'issue_type': issue.issue_type
            },
            description=f"Deleted rental issue {issue.id}",
            request=request
        )
        
        self.log_info(f"Rental issue {issue.id} deleted")
        
        return {"message": "Rental issue deleted successfully"}
    
    def _send_issue_resolved_notification(self, issue: RentalIssue):
        """Send notification to user when issue is resolved"""
        try:
            from api.user.notifications.services import notify
            
            notify(
                issue.rental.user,
                'rental_issue_resolved',
                rental_code=issue.rental.rental_code,
                issue_type=issue.issue_type,
                rental_id=str(issue.rental.id),
                issue_id=str(issue.id)
            )
        except Exception as e:
            self.log_warning(f"Failed to send issue resolved notification: {str(e)}")
    
    def _log_admin_action(
        self,
        admin_user: User,
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
    
    # ============================================================
    # Rental List Methods
    # ============================================================
    
    def get_rentals_list(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get paginated list of rentals with filters
        
        Args:
            filters: Dictionary containing filter parameters
                - status: Filter by rental status
                - payment_status: Filter by payment status
                - user_id: Filter by user ID
                - station_id: Filter by station ID
                - search: Search by rental code or user name
                - recent: 'today', '24h', '7d', '30d' for recent rentals
                - start_date: Filter rentals started after this date
                - end_date: Filter rentals started before this date
                - page: Page number (default: 1)
                - page_size: Items per page (default: 20)
                
        Returns:
            Dict with results and pagination info
        """
        from api.common.utils.helpers import paginate_queryset
        from datetime import timedelta
        from django.db.models import Q
        
        queryset = self._get_base_rental_queryset()
        
        if filters:
            # Status filter
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
            
            # Payment status filter
            if filters.get('payment_status'):
                queryset = queryset.filter(payment_status=filters['payment_status'])
            
            # User filter
            if filters.get('user_id'):
                queryset = queryset.filter(user_id=filters['user_id'])
            
            # Station filter
            if filters.get('station_id'):
                queryset = queryset.filter(
                    Q(station_id=filters['station_id']) | 
                    Q(return_station_id=filters['station_id'])
                )
            
            # Search filter
            if filters.get('search'):
                search_term = filters['search']
                queryset = queryset.filter(
                    Q(rental_code__icontains=search_term) |
                    Q(user__username__icontains=search_term) |
                    Q(user__phone_number__icontains=search_term)
                )
            
            # Recent rentals filter
            if filters.get('recent'):
                now = timezone.now()
                recent_type = filters['recent']
                
                if recent_type == 'today':
                    queryset = queryset.filter(
                        created_at__date=now.date()
                    )
                elif recent_type == '24h':
                    queryset = queryset.filter(
                        created_at__gte=now - timedelta(hours=24)
                    )
                elif recent_type == '7d':
                    queryset = queryset.filter(
                        created_at__gte=now - timedelta(days=7)
                    )
                elif recent_type == '30d':
                    queryset = queryset.filter(
                        created_at__gte=now - timedelta(days=30)
                    )
            
            # Date range filters
            if filters.get('start_date'):
                queryset = queryset.filter(started_at__gte=filters['start_date'])
            
            if filters.get('end_date'):
                queryset = queryset.filter(started_at__lte=filters['end_date'])
        
        # Order by latest first
        queryset = queryset.order_by('-created_at')
        
        # Pagination
        page = filters.get('page', 1) if filters else 1
        page_size = filters.get('page_size', 20) if filters else 20
        
        return paginate_queryset(queryset, page, page_size)
    
    def get_rental_detail(self, rental_id: str):
        """
        Get detailed rental information
        
        Args:
            rental_id: Rental ID (UUID)
            
        Returns:
            Rental instance with all related data
            
        Raises:
            ServiceException: If rental not found
        """
        from api.user.rentals.models import Rental
        
        try:
            return self._get_base_rental_queryset().get(id=rental_id)
        except Rental.DoesNotExist:
            raise ServiceException(
                detail="Rental not found",
                code="rental_not_found"
            )

    @transaction.atomic
    def update_rental_manual_completion(
        self,
        rental_id: str,
        status: str,
        admin_user: User,
        amount=None,
        request=None
    ) -> Rental:
        """
        Simple admin override to adjust amount and status.
        Keeps payment as due when rental is completed manually.
        """
        rental = Rental.objects.select_for_update().filter(id=rental_id).first()
        if not rental:
            raise ServiceException(detail="Rental not found", code="rental_not_found")

        if rental.status == 'COMPLETED':
            raise ServiceException(
                detail="Rental is already completed. No changes were applied.",
                code="rental_already_completed",
                status_code=409
            )

        normalized_status = str(status or '').strip().upper()
        valid_statuses = [choice[0] for choice in Rental.RENTAL_STATUS_CHOICES]
        if normalized_status not in valid_statuses:
            raise ServiceException(
                detail=f"Invalid rental status. Must be one of: {', '.join(valid_statuses)}",
                code="invalid_rental_status"
            )

        old_status = rental.status
        old_payment_status = rental.payment_status
        old_overdue_amount = rental.overdue_amount

        rental.status = normalized_status
        update_fields = ['status', 'updated_at']
        if amount is not None:
            rental.overdue_amount = amount
            update_fields.append('overdue_amount')

        if normalized_status == 'COMPLETED':
            if not rental.ended_at:
                rental.ended_at = timezone.now()
                update_fields.append('ended_at')
            rental.is_returned_on_time = bool(rental.due_at and rental.ended_at and rental.ended_at <= rental.due_at)
            update_fields.append('is_returned_on_time')
            if rental.payment_status != 'PAID':
                rental.payment_status = 'PENDING'
                update_fields.append('payment_status')

            rental.rental_metadata = dict(rental.rental_metadata or {})
            rental.rental_metadata['manual_return_override'] = True
            rental.rental_metadata['manual_return_override_at'] = timezone.now().isoformat()
            rental.rental_metadata['manual_return_override_by_admin'] = str(admin_user.id)
            update_fields.append('rental_metadata')

        rental.save(update_fields=list(dict.fromkeys(update_fields)))

        self._log_admin_action(
            admin_user=admin_user,
            action_type='UPDATE_RENTAL_MANUAL_COMPLETION',
            target_model='Rental',
            target_id=str(rental.id),
            changes={
                'rental_code': rental.rental_code,
                'old_status': old_status,
                'new_status': rental.status,
                'old_payment_status': old_payment_status,
                'new_payment_status': rental.payment_status,
                'old_amount': str(old_overdue_amount),
                'new_amount': str(rental.overdue_amount),
            },
            description=f"Manual rental update: {rental.rental_code} -> {rental.status}",
            request=request
        )

        return rental
    
    def _get_base_rental_queryset(self):
        """Get base queryset with all necessary relationships"""
        from api.user.rentals.models import Rental
        
        return Rental.objects.select_related(
            'user',
            'station',
            'return_station',
            'slot',
            'package',
            'power_bank'
        ).prefetch_related(
            'extensions',
            'issues'
        )
