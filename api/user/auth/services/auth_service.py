from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import generate_unique_code
from api.user.auth.models import User
from api.user.auth.utils.otp_handler import OTPHandler
from api.user.auth.utils.master_otp_validator import is_master_number, validate_master_otp
from api.user.auth.utils.verification_token_handler import VerificationTokenHandler
from api.user.auth.utils.user_identifier_helper import is_email
from api.user.auth.repositories import UserRepository, ProfileRepository
from api.user.auth.services.account_service import AccountService

logger = logging.getLogger(__name__)

class AuthService(BaseService):
    """Service for authentication operations (OTP, Login, Register, Logout, Refresh)"""
    
    def __init__(self):
        super().__init__()
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
        self.account_service = AccountService()

    def generate_otp(self, identifier: str, platform: str = None) -> Dict[str, Any]:
        """Generate and send OTP - automatically detects login vs register"""
        try:
            user_exists = self.user_repo.exists(identifier)
            purpose = 'LOGIN' if user_exists else 'REGISTER'
            
            if is_master_number(identifier):
                self.log_info(f"Master number detected for {identifier} - Purpose: {purpose}")
                return {
                    'message': f'OTP sent successfully for {purpose.lower()}',
                    'purpose': purpose,
                    'expires_in_minutes': OTPHandler.OTP_EXPIRY_MINUTES,
                    'identifier': identifier
                }
            
            OTPHandler.check_rate_limit(identifier)
            otp = OTPHandler.generate_otp()
            OTPHandler.store_otp(identifier, otp, purpose)
            
            from api.user.notifications.services import send_otp
            send_otp(
                identifier=identifier,
                otp=otp,
                purpose=purpose,
                expiry_minutes=OTPHandler.OTP_EXPIRY_MINUTES,
                platform=platform,
                async_send=True
            )
            
            self.log_info(f"OTP generated for {identifier} - Purpose: {purpose}")
            return {
                'message': f'OTP sent successfully for {purpose.lower()}',
                'purpose': purpose,
                'expires_in_minutes': OTPHandler.OTP_EXPIRY_MINUTES,
                'identifier': identifier
            }
            
        except ServiceException: raise
        except Exception as e:
            self.handle_service_error(e, f"Failed to send OTP to {identifier}")

    def verify_otp(self, identifier: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and return verification token"""
        try:
            if validate_master_otp(identifier, otp):
                user_exists = self.user_repo.exists(identifier)
                purpose = 'LOGIN' if user_exists else 'REGISTER'
            else:
                purpose = OTPHandler.validate_otp(identifier, otp)
                OTPHandler.clear_otp(identifier)
            
            verification_token = VerificationTokenHandler.generate_token(identifier, purpose)
            self.log_info(f"OTP verified for {identifier} - Purpose: {purpose}")
            
            return {
                'verification_token': verification_token,
                'message': 'OTP verified successfully',
                'purpose': purpose,
                'identifier': identifier,
                'expires_in_minutes': VerificationTokenHandler.TOKEN_EXPIRY_MINUTES
            }
            
        except ServiceException: raise
        except Exception as e:
            self.handle_service_error(e, f"Failed to verify OTP for {identifier}")

    def complete_auth(self, identifier: str, verification_token: str, username: str = None, referral_code: str = None, request=None) -> Dict[str, Any]:
        """Unified authentication completion - handles both login and registration"""
        try:
            token_data = VerificationTokenHandler.validate_token(identifier, verification_token)
            purpose = token_data['purpose']
            
            if purpose == 'REGISTER':
                return self._handle_registration(identifier, username, verification_token, referral_code, request)
            return self._handle_login(identifier, verification_token, request)
                
        except ServiceException: raise
        except Exception as e:
            self.handle_service_error(e, f"Authentication failed for {identifier}")

    @transaction.atomic
    def _handle_registration(self, identifier: str, username: str, verification_token: str, referral_code: str = None, request=None) -> Dict[str, Any]:
        """Handle user registration"""
        if not username:
            raise ServiceException(detail="Username is required for registration", code="username_required")
        
        if self.user_repo.exists(identifier):
            raise ServiceException(detail="User already exists", code="user_already_exists")
        
        user_data = {'username': username}
        if is_email(identifier):
            user_data['email'] = identifier
            user_data['email_verified'] = True
        else:
            user_data['phone_number'] = identifier
            user_data['phone_verified'] = True
        
        user = self.user_repo.create_user(
            **user_data,
            referral_code=generate_unique_code("REF", 6)
        )
        
        if referral_code:
            self._process_referral(user, referral_code)
        
        self.account_service.initialize_account(user, request=request)
        self._handle_post_registration(user, request)
        
        refresh = RefreshToken.for_user(user)
        VerificationTokenHandler.clear_token(verification_token)
        
        return {
            'message': 'Registration successful',
            'user': self._get_user_base_data(user),
            'tokens': self._get_tokens(refresh)
        }

    def _handle_login(self, identifier: str, verification_token: str, request=None) -> Dict[str, Any]:
        """Handle user login"""
        user = self.user_repo.get_by_identifier(identifier)
        if not user:
            raise ServiceException(detail="User not found", code="user_not_found")
        
        if not user.is_active:
            raise ServiceException(detail="Account is deactivated", code="account_deactivated")
        
        self.user_repo.update_last_login(user)
        refresh = RefreshToken.for_user(user)
        
        if request:
            self.account_service.log_auth_action(user, 'LOGIN', request)
        
        VerificationTokenHandler.clear_token(verification_token)
        
        return {
            'message': 'Login successful',
            'user': self._get_user_base_data(user),
            'tokens': self._get_tokens(refresh)
        }

    def logout_user(self, refresh_token: Optional[str], user: User, request=None) -> Dict[str, Any]:
        """Logout user with best-effort token revocation."""
        token_revoked = False
        revocation_reason = "token_missing"

        normalized_refresh = (refresh_token or "").strip()
        if normalized_refresh:
            try:
                token = RefreshToken(normalized_refresh)
                token_user_id = str(token.payload.get("user_id"))
                if token_user_id != str(user.id):
                    revocation_reason = "token_mismatch"
                    self.log_warning(
                        f"Logout refresh token mismatch for user {user.id}: token user {token_user_id}"
                    )
                else:
                    token.blacklist()
                    token_revoked = True
                    revocation_reason = "valid_blacklisted"
            except (TokenError, InvalidToken):
                revocation_reason = "already_invalid"
                self.log_warning(f"Logout token already invalid for user {user.id}")
            except Exception as e:
                revocation_reason = "already_invalid"
                self.log_warning(f"Unexpected logout revocation issue for user {user.id}: {str(e)}")

        if request:
            try:
                self.account_service.log_auth_action(user, 'LOGOUT', request)
            except Exception as e:
                self.log_warning(f"Failed to write logout audit for user {user.id}: {str(e)}")

        return {
            'message': 'Logout successful',
            'logged_out_at': timezone.now().isoformat(),
            'token_revoked': token_revoked,
            'revocation_reason': revocation_reason
        }

    def refresh_token(self, refresh_token: str, request=None) -> Dict[str, Any]:
        """Refresh access token"""
        try:
            if not refresh_token:
                raise ServiceException(detail="Invalid refresh token", code="invalid_refresh_token")

            refresh = RefreshToken(refresh_token)
            user_id = refresh.payload.get('user_id')
            user = self.user_repo.get_by_id(user_id)
            
            if not user or not user.is_active:
                raise ServiceException(detail="User not found or inactive", code="user_invalid")
            
            if request:
                self.account_service.log_auth_action(user, 'TOKEN_REFRESH', request)
            
            return {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': self._get_user_base_data(user),
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
        except (TokenError, InvalidToken):
            raise ServiceException(detail="Invalid refresh token", code="invalid_refresh_token")
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Token refresh failed")

    def _handle_post_registration(self, user: User, request=None):
        """Handle post-registration tasks"""
        from api.user.points.services import award_points
        from api.user.system.services import AppConfigService
        
        points = int(AppConfigService().get_config_cached('POINTS_SIGNUP', 50))
        transaction.on_commit(lambda: award_points(user, points, 'SIGNUP', 'Signup bonus', async_send=True))
        
        # Audit logging is now handled by account_service.initialize_account

    def _get_user_base_data(self, user: User) -> Dict[str, Any]:
        return {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'is_active': user.is_active
        }

    def _get_tokens(self, refresh: RefreshToken) -> Dict[str, str]:
        return {'access': str(refresh.access_token), 'refresh': str(refresh)}

    def _process_referral(self, user: User, referral_code: str) -> None:
        """Process referral during registration"""
        if not referral_code:
            return
            
        try:
            from api.user.points.services.referral_service import ReferralService
            referral_service = ReferralService()
            
            # Validate and get inviter
            validation_result = referral_service.validate_referral_code(referral_code, requesting_user=user)
            
            if validation_result.get('valid'):
                inviter_id = validation_result.get('inviter_id')
                inviter = User.objects.get(id=inviter_id)
                
                # Create referral link
                referral_service.create_referral(inviter, user, referral_code)
                self.log_info(f"Referral link created for user {user.username} from {inviter.username}")
                
        except Exception as e:
            # We don't want to block registration if referral fails
            self.log_warning(f"Failed to process referral for user {user.username}: {str(e)}")
