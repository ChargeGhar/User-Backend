"""
Service for admin referral management
============================================================

This module contains service classes for admin referral management operations.
Wraps points app referral services with admin-specific features.

Created: 2025-11-11
"""
from __future__ import annotations

from typing import Dict, Any
from django.db import transaction

from api.common.services.base import CRUDService, ServiceException
from api.admin.models import AdminActionLog
from api.user.points.models import Referral
from api.user.auth.models import User


class AdminReferralService(CRUDService):
    """Service for admin referral management"""
    model = Referral
    
    def __init__(self):
        super().__init__()
        from api.user.points.services import ReferralService
        self.referral_service = ReferralService()
    
    def get_referral_analytics(
        self,
        start_date=None,
        end_date=None
    ) -> Dict[str, Any]:
        """
        Get comprehensive referral analytics
        
        Args:
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            
        Returns:
            Dict with referral analytics
        """
        try:
            # Use core referral service for analytics
            date_range = None
            if start_date and end_date:
                date_range = (start_date, end_date)
            
            analytics = self.referral_service.get_referral_analytics(date_range)
            
            return analytics
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get referral analytics")
    
    def get_user_referrals(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get referrals sent by a specific user
        
        Args:
            user_id: User ID to get referrals for
            page: Page number
            page_size: Items per page
            
        Returns:
            Paginated list of referrals
        """
        try:
            # Get user
            user = User.objects.get(id=user_id)
            
            # Use core referral service
            referrals = self.referral_service.get_user_referrals(
                user=user,
                page=page,
                page_size=page_size
            )
            
            return referrals
            
        except User.DoesNotExist:
            raise ServiceException(
                detail="User not found",
                code="user_not_found",
                status_code=404,
                user_message="The specified user does not exist"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get user referrals")
    
    @transaction.atomic
    def complete_referral(
        self,
        referral_id: str,
        admin_user
    ) -> Dict[str, Any]:
        """
        Manually complete a referral (admin override)
        
        Args:
            referral_id: Referral ID to complete
            admin_user: Admin user completing the referral
            
        Returns:
            Dict with completion details
        """
        try:
            # Get referral
            referral = Referral.objects.select_related('inviter', 'invitee').get(id=referral_id)
            
            # Check if already completed
            if referral.status == 'COMPLETED':
                raise ServiceException(
                    detail="Referral is already completed",
                    code="referral_already_completed",
                    status_code=400,
                    user_message="This referral has already been completed"
                )
            
            # Check if expired
            if referral.status == 'EXPIRED':
                raise ServiceException(
                    detail="Cannot complete an expired referral",
                    code="referral_expired",
                    status_code=400,
                    user_message="This referral has expired and cannot be completed"
                )
            
            # Store old status
            old_status = referral.status
            
            # Use core referral service to complete
            result = self.referral_service.complete_referral(
                referral_id=referral_id,
                rental=None  # Admin manual completion
            )
            
            # Log admin action
            self._log_admin_action(
                admin_user=admin_user,
                action_type='COMPLETE_REFERRAL',
                target_model='Referral',
                target_id=str(referral.id),
                changes={
                    'old_status': old_status,
                    'new_status': 'COMPLETED',
                    'inviter': referral.inviter.username,
                    'invitee': referral.invitee.username,
                    'inviter_points': result['inviter_points'],
                    'invitee_points': result['invitee_points'],
                    'manual_completion': True
                },
                description=f"Manually completed referral: {referral.inviter.username} -> {referral.invitee.username}"
            )
            
            self.log_info(
                f"Referral manually completed by admin {admin_user.username}: "
                f"{referral.inviter.username} -> {referral.invitee.username}"
            )
            
            return {
                **result,
                'manual_completion': True,
                'completed_by_admin': admin_user.username
            }
            
        except Referral.DoesNotExist:
            raise ServiceException(
                detail="Referral not found",
                code="referral_not_found",
                status_code=404,
                user_message="The specified referral does not exist"
            )
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to complete referral")
    
    def _log_admin_action(
        self,
        admin_user,
        action_type: str,
        target_model: str,
        target_id: str,
        changes: Dict[str, Any],
        description: str = ""
    ) -> None:
        """Log admin action for audit trail"""
        try:
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type=action_type,
                target_model=target_model,
                target_id=target_id,
                changes=changes,
                description=description,
                ip_address="127.0.0.1",  # Should be passed from request
                user_agent="Admin Panel"  # Should be passed from request
            )
        except Exception as e:
            self.log_error(f"Failed to log admin action: {str(e)}")
