from __future__ import annotations
from typing import Dict, Any, List
from django.db import transaction

from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import validate_phone_number
from api.user.auth.models import User, UserProfile
from api.user.auth.repositories import ProfileRepository, UserRepository
from api.user.payments.repositories.wallet_repository import WalletRepository
from api.user.points.repositories.point_repository import PointRepository

class UserProfileService(BaseService):
    """Service for user profile and related comprehensive data operations"""
    
    def __init__(self):
        super().__init__()
        self.profile_repo = ProfileRepository()
        self.user_repo = UserRepository()
        self.wallet_repo = WalletRepository()
        self.point_repo = PointRepository()

    @transaction.atomic
    def update_profile(self, user: User, validated_data: Dict[str, Any]) -> UserProfile:
        """Update user profile and contact fields based on provider rules."""
        try:
            profile = self.profile_repo.get_by_user_id(user.id)
            if not profile:
                profile = self.profile_repo.create_profile(user=user)

            was_complete = profile.is_profile_complete
            missing = object()
            requested_email = validated_data.pop('email', missing)
            requested_phone = validated_data.pop('phone_number', missing)

            contact_updates = self._resolve_contact_updates(
                user=user,
                requested_email=requested_email,
                requested_phone=requested_phone,
                missing=missing
            )

            user_update_fields = []

            # Update profile fields
            for field, value in validated_data.items():
                if value is not None:
                    setattr(profile, field, value)

                    # Sync avatar_url to user.profile_picture for consistency
                    if field == 'avatar_url' and user.profile_picture != value:
                        user.profile_picture = value
                        user_update_fields.append('profile_picture')

            # Apply user contact updates
            for field, value in contact_updates.items():
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    user_update_fields.append(field)

            if user_update_fields:
                user.save(update_fields=list(set(user_update_fields)))

            # Check completeness
            required_fields = ['full_name', 'date_of_birth', 'address']
            profile.is_profile_complete = all(getattr(profile, field) for field in required_fields)
            profile.save()

            if profile.is_profile_complete and not was_complete:
                self._award_profile_completion_points(user)
            elif not profile.is_profile_complete:
                self._send_completion_reminder(user, profile)

            self.log_info(f"Profile updated for user: {user.username}")
            return profile
        except Exception as e:
            self.handle_service_error(e, "Failed to update profile")

    def _resolve_contact_updates(
        self,
        user: User,
        requested_email: Any,
        requested_phone: Any,
        missing: object
    ) -> Dict[str, str]:
        """Validate and resolve contact-field updates by social provider policy."""
        provider = (user.social_provider or '').upper()
        updates: Dict[str, str] = {}

        if requested_email is not missing:
            if requested_email is None:
                raise ServiceException(
                    detail="Email cannot be cleared from profile",
                    code="email_immutable"
                )

            email = str(requested_email).strip().lower()
            current_email = (user.email or '').strip().lower()

            if provider in ('GOOGLE', 'APPLE'):
                if email != current_email:
                    raise ServiceException(
                        detail="Email cannot be changed for social-login accounts",
                        code="email_immutable"
                    )
            elif provider == 'EMAIL':
                if email != current_email:
                    raise ServiceException(
                        detail="Primary email cannot be changed",
                        code="email_immutable"
                    )
            elif provider == 'PHONE':
                if current_email:
                    if email != current_email:
                        raise ServiceException(
                            detail="Email is already set and cannot be changed",
                            code="email_immutable"
                        )
                else:
                    self._ensure_email_available(user=user, email=email)
                    updates['email'] = email
            else:
                if current_email and email != current_email:
                    raise ServiceException(
                        detail="Email cannot be changed",
                        code="email_immutable"
                    )
                if not current_email:
                    self._ensure_email_available(user=user, email=email)
                    updates['email'] = email

        if requested_phone is not missing:
            if requested_phone is None:
                raise ServiceException(
                    detail="Phone number cannot be cleared from profile",
                    code="phone_immutable"
                )

            phone = str(requested_phone).strip()
            current_phone = (user.phone_number or '').strip()

            if not phone:
                raise ServiceException(
                    detail="Phone number cannot be empty",
                    code="invalid_phone_number"
                )

            if not validate_phone_number(phone):
                raise ServiceException(
                    detail="Invalid phone number format",
                    code="invalid_phone_number"
                )

            if provider == 'PHONE':
                if phone != current_phone:
                    raise ServiceException(
                        detail="Primary phone number cannot be changed",
                        code="phone_immutable"
                    )
            elif provider in ('EMAIL', 'GOOGLE', 'APPLE'):
                if current_phone:
                    if phone != current_phone:
                        raise ServiceException(
                            detail="Phone number is already set and cannot be changed",
                            code="phone_immutable"
                        )
                else:
                    self._ensure_phone_available(user=user, phone=phone)
                    updates['phone_number'] = phone
            else:
                if current_phone and phone != current_phone:
                    raise ServiceException(
                        detail="Phone number cannot be changed",
                        code="phone_immutable"
                    )
                if not current_phone:
                    self._ensure_phone_available(user=user, phone=phone)
                    updates['phone_number'] = phone

        return updates

    def _ensure_email_available(self, user: User, email: str) -> None:
        """Ensure email is not already used by another user."""
        if User.objects.filter(email=email).exclude(id=user.id).exists():
            raise ServiceException(
                detail="Email is already in use",
                code="email_already_exists"
            )

    def _ensure_phone_available(self, user: User, phone: str) -> None:
        """Ensure phone number is not already used by another user."""
        if User.objects.filter(phone_number=phone).exclude(id=user.id).exists():
            raise ServiceException(
                detail="Phone number is already in use",
                code="phone_already_exists"
            )

    def get_detailed_profile(self, user: User) -> Dict[str, Any]:
        """Consolidate user data for /me endpoint"""
        try:
            wallet_summary = self.get_wallet_summary(user)
            eligibility = self.check_rental_eligibility(user)
            points_summary = self._get_points_summary(user)
            
            # Ensure profile exists
            profile = self.profile_repo.get_by_user_id(user.id)
            if not profile:
                profile = self.profile_repo.create_profile(user=user)
                
            return {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'profile_picture': user.profile_picture or profile.avatar_url,
                'referral_code': user.referral_code,
                'status': user.status,
                'social_provider': user.social_provider,
                'date_joined': user.date_joined,
                'profile': {
                    'full_name': profile.full_name,
                    'date_of_birth': profile.date_of_birth,
                    'address': profile.address,
                    'avatar_url': profile.avatar_url,
                    'completed': profile.is_profile_complete
                },
                'kyc': self.get_kyc_summary(user),
                'wallet': wallet_summary,
                'points': points_summary,
                'rental_eligibility': eligibility
            }
        except Exception as e:
            self.handle_service_error(e, "Failed to get detailed profile")

    def get_kyc_summary(self, user: User) -> Dict[str, Any]:
        """Get summarized KYC status for the user"""
        try:
            kyc = getattr(user, 'kyc', None)
            if not kyc:
                return {
                    'status': 'NOT_SUBMITTED',
                    'verified': False,
                    'document_number': None,
                    'document_front_url': None,
                    'font_face_url': None,
                    'document_back_url': None,
                    'document_type': None,
                    'verified_at': None,
                    'rejection_reason': None
                }
            
            return {
                'document_number': kyc.document_number,
                'document_front_url': kyc.document_front_url,
                'font_face_url': kyc.font_face_url,
                'document_back_url': kyc.document_back_url,
                'document_type': kyc.document_type,
                'status': kyc.status,
                'verified_at': kyc.verified_at,
                'rejection_reason': kyc.rejection_reason if kyc.status == 'REJECTED' else None,
                'verified': kyc.status == 'APPROVED'
            }
        except Exception:
            return {'status': 'NOT_SUBMITTED', 'verified': False}

    def check_rental_eligibility(self, user: User) -> Dict[str, Any]:
        """Check if user is eligible to rent a powerbank"""
        from api.user.system.services.app_config_service import AppConfigService
        from api.user.rentals.models import Rental
        
        config = AppConfigService()
        need_profile = config.get_config_cached('NEED_RENTALS_PROFILE_COMPLETE', 'true').lower() in ['true', '1', 'yes']
        need_kyc = config.get_config_cached('NEED_RENTALS_KYC_VERIFIED', 'true').lower() in ['true', '1', 'yes']
        
        profile_complete = hasattr(user, 'profile') and user.profile.is_profile_complete
        kyc_approved = hasattr(user, 'kyc') and user.kyc.status == 'APPROVED'
        is_active = user.status == 'ACTIVE'
        has_pending_dues = Rental.objects.filter(user=user, payment_status='PENDING', status__in=['OVERDUE', 'COMPLETED']).exists()
        
        can_rent = (is_active and not has_pending_dues and (not need_profile or profile_complete) and (not need_kyc or kyc_approved))
        
        reasons = []
        if not is_active: reasons.append('Account not active')
        if has_pending_dues: reasons.append('Pending dues')
        if need_profile and not profile_complete: reasons.append('Complete profile')
        if need_kyc and not kyc_approved: reasons.append('Verify KYC')
        
        return {'can_rent': can_rent, 'reasons': reasons}

    def get_wallet_summary(self, user: User) -> Dict[str, Any]:
        """Get wallet balance and topup history"""
        try:
            wallet, _ = self.wallet_repo.get_or_create(user=user)
            total_topup = self.wallet_repo.get_total_topup(str(user.id))
            return {
                'balance': str(wallet.balance), 
                'total_topup': str(total_topup), 
                'currency': wallet.currency
            }
        except Exception as e:
            self.log_error(f"Wallet summary failed: {str(e)}")
            return {'balance': '0.00', 'total_topup': '0.00', 'currency': 'NPR'}

    def get_user_analytics(self, user: User) -> Dict[str, Any]:
        """Get user usage analytics"""
        from api.user.rentals.models import Rental
        from api.user.stations.models import UserStationFavorite
        from api.user.payments.models import Transaction
        
        rentals = Rental.objects.filter(user=user)
        total_rentals = rentals.count()
        timely_returns = rentals.filter(is_returned_on_time=True).count()
        
        transactions = Transaction.objects.filter(user=user, status='SUCCESS', transaction_type__in=['RENTAL', 'TOPUP'])
        total_spent = sum(t.amount for t in transactions)
        
        return {
            'total_rentals': total_rentals,
            'total_spent': total_spent,
            'total_points_earned': getattr(user.points, 'total_points', 0) if hasattr(user, 'points') else 0,
            'total_referrals': self.user_repo.count_referrals(user),
            'timely_returns': timely_returns,
            'late_returns': total_rentals - timely_returns,
            'favorite_stations_count': UserStationFavorite.objects.filter(user=user).count(),
            'last_rental_date': rentals.order_by('-created_at').values_list('created_at', flat=True).first(),
            'member_since': user.date_joined
        }

    def _get_points_summary(self, user: User) -> Dict[str, Any]:
        try:
            points, _ = self.point_repo.get_or_create(user=user)
            return {'current': points.current_points, 'total_earned': points.total_points}
        except:
            return {'current': 0, 'total_earned': 0}

    def _award_profile_completion_points(self, user: User):
        from api.user.points.services import award_points
        from api.user.system.services import AppConfigService
        points = int(AppConfigService().get_config_cached('POINTS_PROFILE', 20))
        transaction.on_commit(lambda: award_points(user, points, 'PROFILE', 'Profile completed', async_send=True))

    def _send_completion_reminder(self, user: User, profile: UserProfile):
        from api.user.notifications.services import notify
        required = ['full_name', 'date_of_birth', 'address']
        filled = sum(1 for f in required if getattr(profile, f))
        percentage = int((filled / len(required)) * 100)
        notify(user, 'profile_completion_reminder', async_send=True, completion_percentage=percentage)
