"""
RentalIssueService - Issue Reporting Service
============================================================

Handles reporting and management of rental issues.

Business Logic:
- Report powerbank or rental issues
- Track issue status (reported, in progress, resolved)
- Notify admins of reported issues
- Maintain issue history for quality control

Author: Service Splitter (Cleaned)
Date: 2025-10-17
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any
from django.db import transaction
from django.contrib.auth import get_user_model

from api.common.services.base import CRUDService, ServiceException
from api.user.rentals.models import RentalIssue, Rental

if TYPE_CHECKING:
    from api.user.auth.models import User

User = get_user_model()


class RentalIssueService(CRUDService):
    """Service for rental issue operations"""
    
    model = RentalIssue
    
    @transaction.atomic
    def report_issue(
        self,
        rental_id: str,
        user: User,
        validated_data: Dict[str, Any]
    ) -> RentalIssue:
        """
        Report an issue with a rental.
        
        Args:
            rental_id: UUID of the rental with issues
            user: User reporting the issue
            validated_data: Dictionary containing:
                - issue_type: Type of issue (DAMAGE, MALFUNCTION, etc.)
                - description: Detailed description
                - images: Optional list of image URLs
        
        Returns:
            RentalIssue: Created issue record
        
        Raises:
            ServiceException: If rental not found
        
        Side Effects:
            - Sends notification to all admin users
        """
        try:
            # Validate rental exists and belongs to user
            rental = Rental.objects.get(id=rental_id, user=user)
            
            # Create issue record
            issue = RentalIssue.objects.create(
                rental=rental,
                **validated_data
            )
            
            # Notify all admins about the reported issue
            self._notify_admins_of_issue(rental, issue, user)
            
            self.log_info(
                f"Rental issue reported: {rental.rental_code} - "
                f"{issue.issue_type} by {user.username}"
            )
            
            return issue
            
        except Rental.DoesNotExist:
            raise ServiceException(
                detail="Rental not found",
                code="rental_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to report rental issue")
    
    def _notify_admins_of_issue(
        self,
        rental: Rental,
        issue: RentalIssue,
        user: User
    ) -> None:
        """Send notification to all admin users about reported issue"""
        try:
            from api.user.notifications.services import notify_bulk
            
            # Get all active admin users
            admin_users = User.objects.filter(
                is_staff=True,
                is_active=True
            )
            
            if admin_users.exists():
                # Send bulk notification
                notify_bulk(
                    admin_users,
                    'rental_issue_reported',
                    async_send=True,
                    rental_code=rental.rental_code,
                    issue_type=issue.get_issue_type_display(),
                    user_name=user.username
                )
                
                self.log_info(
                    f"Admin notification sent for issue: {issue.id}"
                )
        except Exception as e:
            # Log error but don't fail the issue creation
            self.log_error(
                f"Failed to notify admins of issue: {str(e)}"
            )
