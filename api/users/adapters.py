from __future__ import annotations

import logging
from typing import Any, Dict

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.http import HttpRequest

User = get_user_model()
logger = logging.getLogger(__name__)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom adapter to integrate social auth with existing User model"""
    
    def pre_social_login(self, request: HttpRequest, sociallogin) -> None:
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.
        """
        # Get social account data
        social_account = sociallogin.account
        provider = social_account.provider
        extra_data = social_account.extra_data
        
        # Try to find existing user by email
        email = extra_data.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                
                # Use service method to link social account
                from api.users.services import SocialAuthService
                auth_service = SocialAuthService()
                linked_user = auth_service.link_social_account(user, extra_data, provider)
                
                sociallogin.user = linked_user
                logger.info(f"Linked {provider} account to existing user: {user.email}")
                
            except User.DoesNotExist:
                # User doesn't exist, will be created in populate_user
                pass
            except Exception as e:
                logger.error(f"Error linking social account: {e}")
                # Continue with normal flow if linking fails
    
    def populate_user(self, request: HttpRequest, sociallogin, data: Dict[str, Any]):
        """
        Populates user information from social provider data.
        """
        social_account = sociallogin.account
        provider = social_account.provider
        extra_data = social_account.extra_data
        
        # Double-check if user already exists by email before creating
        email = extra_data.get('email')
        if email:
            try:
                existing_user = User.objects.get(email=email)
                logger.info(f"Found existing user during populate: {existing_user.email}")
                # Link social account to existing user
                from api.users.services import SocialAuthService
                auth_service = SocialAuthService()
                return auth_service.link_social_account(existing_user, extra_data, provider)
            except User.DoesNotExist:
                pass  # User doesn't exist, proceed with creation
        
        # Use service method to create social user
        try:
            from api.users.services import SocialAuthService
            auth_service = SocialAuthService()
            user = auth_service.create_social_user(extra_data, provider)
            
            logger.info(f"Created new user from {provider}: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating social user via service: {e}")
            
            # Final fallback - check once more for existing user
            if email:
                try:
                    existing_user = User.objects.get(email=email)
                    logger.info(f"Found existing user in fallback: {existing_user.email}")
                    return existing_user
                except User.DoesNotExist:
                    pass
            
            # Manual creation as last resort
            uid = social_account.uid
            
            user = User()
            user.email = email
            user.username = email.split('@')[0] if email else f"{provider}_{uid}"
            user.profile_picture = extra_data.get('picture', '')
            user.email_verified = True
            user.social_provider = provider.upper()
            user.social_profile_data = extra_data
            setattr(user, f'{provider}_id', uid)
            
            logger.info(f"Created new user from {provider} (fallback): {email}")
            return user
    
    def save_user(self, request: HttpRequest, sociallogin, form=None):
        """
        Saves a newly signed up social login user.
        """
        user = sociallogin.user
        
        # If user was created via service method, related objects are already created
        if hasattr(user, '_created_via_service'):
            # User and related objects already created by service
            logger.info(f"Social user already processed by service: {user.email}")
            return user
        
        # Fallback: Save user and create related objects manually
        user.save()
        
        from api.users.models import UserProfile
        from api.points.models import UserPoints
        from api.payments.models import Wallet
        
        try:
            # Create related objects
            profile_data = {
                'full_name': user.social_profile_data.get('name', ''),
                'avatar_url': user.social_profile_data.get('picture', '')
            }
            UserProfile.objects.create(user=user, **profile_data)
            UserPoints.objects.create(user=user)
            Wallet.objects.create(user=user)
            
            # Award signup points (after transaction commits)
            from api.points.services import award_points
            from django.db import transaction
            
            # Schedule task after transaction commits to ensure user exists
            transaction.on_commit(
                lambda: award_points(user, 50, 'SOCIAL_SIGNUP', f'New user signup via {sociallogin.account.provider}', async_send=True)
            )
            
            # Send welcome message
            from api.users.tasks import send_social_auth_welcome_message
            send_social_auth_welcome_message.delay(user.id, sociallogin.account.provider)
            
        except Exception as e:
            logger.error(f"Error creating related objects for social user: {e}")
        
        logger.info(f"Saved social user and created profile: {user.email}")
        return user