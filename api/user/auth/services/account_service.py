import uuid
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

    @transaction.atomic
    def delete_account(self, user, request=None) -> None:
        """
        Soft-delete a user account.

        Instead of hard-deleting (which would cascade-wipe financial records,
        rentals, transactions, audit logs, etc.), we:
          1. Anonymize all PII fields             (atomic)
          2. Deactivate the account               (atomic)
          3. Delete device tokens                 (atomic)
          4. Log the deletion action              (best-effort, outside atomic)

        The user row is KEPT so foreign-key references from transactions,
        rentals, payments, and audit logs remain intact.
        """
        user_id = user.id  # capture before the atomic block mutates state

        # Phase 1 — critical ops wrapped in their own atomic block
        self._anonymize_and_deactivate(user)

        # Phase 2 — best-effort audit log; runs AFTER the transaction commits
        # so a failing INSERT here cannot roll back the anonymization above.
        try:
            if request:
                self.audit_repo.create_log(
                    user=user,
                    action='DELETE',
                    entity_type='USER',
                    entity_id=str(user_id),
                    request=request
                )
        except Exception as audit_err:
            self.log_warning(f"Audit log failed for account deletion {user_id}: {audit_err}")

        self.log_info(f"Account soft-deleted: id={user_id}, anonymized to {user.username}")

    @transaction.atomic
    def _anonymize_and_deactivate(self, user) -> None:
        """
        Atomically anonymize PII and deactivate.
        Kept separate from audit logging so a log failure cannot
        trigger a TransactionManagementError that rolls back the wipe.
        """
        from api.user.auth.models import UserDevice

        uid = uuid.uuid4().hex[:10]

        # Anonymize PII — placeholder email satisfies the DB CHECK constraint
        # (user_must_have_identifier: email OR phone must be non-null)
        user.email = f"deleted_{uid}@deleted.local"
        user.phone_number = None
        user.username = f"deleted_{uid}"
        user.profile_picture = None
        user.google_id = None
        user.apple_id = None
        user.referral_code = None

        # Deactivate
        user.is_active = False
        user.status = 'INACTIVE'

        user.save(update_fields=[
            'email', 'phone_number', 'username', 'profile_picture',
            'google_id', 'apple_id', 'referral_code',
            'is_active', 'status',
        ])

        # Wipe device tokens → invalidates biometric sessions.
        # Outstanding JWT access tokens expire naturally;
        # refresh tokens are rejected because is_active=False.
        UserDevice.objects.filter(user=user).delete()
