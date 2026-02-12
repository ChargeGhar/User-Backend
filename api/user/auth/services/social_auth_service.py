from typing import Dict, Any
import logging
from django.db import transaction
from api.common.services.base import BaseService
from api.common.utils.helpers import generate_unique_code
from api.user.auth.models import User
from api.user.auth.repositories import UserRepository, ProfileRepository
from api.user.auth.services.account_service import AccountService

logger = logging.getLogger(__name__)

class SocialAuthService(BaseService):
    """Service for social authentication operations (Google, Apple)"""
    
    def __init__(self):
        super().__init__()
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
        self.account_service = AccountService()

    @transaction.atomic
    def create_social_user(self, social_data: Dict[str, Any], provider: str) -> User:
        """Create user from social authentication data"""
        try:
            email = social_data.get('email')
            name = social_data.get('name', '')
            picture = social_data.get('picture', '')
            provider_id = social_data.get('id') or social_data.get('sub')
            
            if email:
                existing_user = self.user_repo.get_by_identifier(email)
                if existing_user:
                    self.log_info(f"User with email {email} already exists, linking social account")
                    return self.link_social_account(existing_user, social_data, provider)
            
            base_username = email.split('@')[0] if email else f"{provider}_{provider_id}"
            username = self._generate_unique_username(base_username)
            
            user = self.user_repo.create_user(
                username=username,
                email=email,
                profile_picture=picture,
                social_provider=provider.upper(),
                social_profile_data=social_data,
                referral_code=generate_unique_code("REF", 6),
                email_verified=True
            )
            setattr(user, f'{provider}_id', provider_id)
            user.save()
            
            self.account_service.initialize_account(
                user, 
                full_name=name, 
                avatar_url=picture
            )
            
            self._handle_post_registration(user, provider)
            # Signal adapter that related objects are already initialized.
            user._created_via_service = True
            return user
            
        except Exception as e:
            self.handle_service_error(e, f"Failed to create social user via {provider}")

    def link_social_account(self, user: User, social_data: Dict[str, Any], provider: str) -> User:
        """Link social account to existing user"""
        try:
            provider_id = social_data.get('id') or social_data.get('sub')
            provider_id_field = f'{provider}_id'
            
            if not getattr(user, provider_id_field, None):
                setattr(user, provider_id_field, provider_id)
                user.social_provider = provider.upper()
                user.social_profile_data = social_data
                if not user.profile_picture:
                    user.profile_picture = social_data.get('picture')
                user.save()
            
            profile = self.profile_repo.get_by_user_id(user.id)
            if profile:
                self.profile_repo.update_profile(
                    profile, 
                    full_name=profile.full_name or social_data.get('name'),
                    avatar_url=profile.avatar_url or social_data.get('picture')
                )
            else:
                self.profile_repo.create_profile(
                    user=user,
                    full_name=social_data.get('name', ''),
                    avatar_url=social_data.get('picture', '')
                )
            
            self.account_service.wallet_repo.get_or_create(user=user)
            self.account_service.point_repo.get_or_create(user=user)
            
            self.log_info(f"Social account linked: {user.username} with {provider}")
            # Signal adapter that service handled social account linking path.
            user._created_via_service = True
            return user
        except Exception as e:
            self.handle_service_error(e, f"Failed to link social account via {provider}")

    def _generate_unique_username(self, base_username: str) -> str:
        """Generate unique username using repository"""
        username = base_username
        counter = 1
        while self.user_repo.exists_by_username(username):
            username = f"{base_username}_{counter}"
            counter += 1
        return username

    def _handle_post_registration(self, user: User, provider: str):
        """Handle tasks after social registration"""
        from api.user.points.services import award_points
        from api.user.auth.tasks import send_social_auth_welcome_message
        
        transaction.on_commit(lambda: award_points(user, 50, 'SOCIAL_SIGNUP', f'New user signup via {provider}', async_send=True))
        transaction.on_commit(lambda: send_social_auth_welcome_message.delay(user.id, provider))
