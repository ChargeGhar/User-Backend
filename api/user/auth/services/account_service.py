from typing import Dict, Any, Optional
from django.db import transaction
from api.common.services.base import BaseService
from api.user.auth.repositories import ProfileRepository, UserRepository
from api.user.payments.repositories.wallet_repository import WalletRepository
from api.user.points.repositories.point_repository import PointRepository
from api.user.system.repositories.audit_repository import AuditRepository

class AccountService(BaseService):
    """Service for cross-cutting account operations (initialization, auditing)"""
    
    def __init__(self):
        super().__init__()
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
        self.wallet_repo = WalletRepository()
        self.point_repo = PointRepository()
        self.audit_repo = AuditRepository()

    @transaction.atomic
    def initialize_account(self, user, full_name: str = '', avatar_url: str = '', request=None) -> None:
        """Initialize all related records for a new user account"""
        # Create Profile
        self.profile_repo.create_profile(
            user=user, 
            full_name=full_name, 
            avatar_url=avatar_url
        )
        
        # Create Wallet
        self.wallet_repo.get_or_create(user=user)
        
        # Create Points record
        self.point_repo.get_or_create(user=user)
        
        # Log creation
        if request:
            self.audit_repo.create_log(
                user=user,
                action='CREATE',
                entity_type='USER',
                entity_id=str(user.id),
                request=request
            )
        
        self.log_info(f"Account initialized for user: {user.username}")

    def log_auth_action(self, user, action: str, request) -> None:
        """Log authentication related actions (LOGIN, LOGOUT, etc)"""
        self.audit_repo.create_log(
            user=user,
            action=action,
            entity_type='USER',
            entity_id=str(user.id),
            request=request
        )
