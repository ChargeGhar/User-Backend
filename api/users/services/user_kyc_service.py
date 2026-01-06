from __future__ import annotations
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from api.common.services.base import BaseService
from api.users.models import User, UserKYC
from api.notifications.services import notify
from api.users.repositories import ProfileRepository

class UserKYCService(BaseService):
    """Service for KYC operations"""
    
    def __init__(self):
        super().__init__()
        self.profile_repo = ProfileRepository()
    
    @transaction.atomic
    def submit_kyc(self, user: User, validated_data: Dict[str, Any]) -> UserKYC:
        """Submit KYC documents"""
        try:
            kyc = self.profile_repo.get_kyc_by_user_id(user.id)
            
            if kyc:
                validated_data['status'] = 'PENDING'
                kyc = self.profile_repo.update_kyc(kyc, **validated_data)
            else:
                kyc, _ = self.profile_repo.create_or_update_kyc(user, **validated_data)
            
            self.log_info(f"KYC submitted for user: {user.username}")
            return kyc
            
        except Exception as e:
            self.handle_service_error(e, "Failed to submit KYC")
    
    def get_kyc_status(self, user: User) -> Dict[str, Any]:
        """Get KYC status for user"""
        kyc = self.profile_repo.get_kyc_by_user_id(user.id)
        if kyc:
            return {
                'status': kyc.status,
                'submitted_at': kyc.created_at,
                'verified_at': kyc.verified_at,
                'rejection_reason': kyc.rejection_reason
            }
        return {'status': 'NOT_SUBMITTED', 'submitted_at': None, 'verified_at': None, 'rejection_reason': None}
    
    def update_kyc_status(self, user: User, status: str, rejection_reason: str = None) -> bool:
        """Update KYC status and send notification"""
        try:
            kyc = self.profile_repo.get_kyc_by_user_id(user.id)
            if not kyc:
                self.log_error(f"KYC not found for user {user.username}")
                return False
            
            update_data = {'status': status}
            if rejection_reason:
                update_data['rejection_reason'] = rejection_reason
            if status == 'APPROVED':
                update_data['verified_at'] = timezone.now()
                self._award_kyc_points(user)
                
            self.profile_repo.update_kyc(kyc, **update_data)
            
            notify(
                user,
                'kyc_status_update',
                async_send=True,
                kyc_status=status.lower(),
                rejection_reason=rejection_reason
            )
            
            self.log_info(f"KYC status updated: {user.username} -> {status}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to update KYC status: {str(e)}")
            return False

    def _award_kyc_points(self, user: User):
        from api.points.services import award_points
        from api.system.services import AppConfigService
        kyc_points = int(AppConfigService().get_config_cached('POINTS_KYC', 30))
        transaction.on_commit(lambda: award_points(user, kyc_points, 'KYC', 'KYC verification completed', async_send=True))
