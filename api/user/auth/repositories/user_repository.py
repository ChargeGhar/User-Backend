from typing import Optional, List
from django.db.models import Q
from api.user.auth.models import User

class UserRepository:
    """Repository for User data operations"""
    
    @staticmethod
    def get_by_id(user_id: str) -> Optional[User]:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_identifier(identifier: str) -> Optional[User]:
        """Get user by email, phone, or username"""
        return User.objects.filter(
            Q(email=identifier) | 
            Q(phone_number=identifier) | 
            Q(username=identifier)
        ).first()

    @staticmethod
    def exists(identifier: str) -> bool:
        """Check if user exists by email, phone, or username"""
        return User.objects.filter(
            Q(email=identifier) | 
            Q(phone_number=identifier) | 
            Q(username=identifier)
        ).exists()

    @staticmethod
    def exists_by_username(username: str) -> bool:
        """Check if username exists"""
        return User.objects.filter(username=username).exists()

    @staticmethod
    def exists_by_email(email: str) -> bool:
        """Check if email exists"""
        return User.objects.filter(email=email).exists()

    @staticmethod
    def exists_by_phone(phone_number: str) -> bool:
        """Check if phone number exists"""
        return User.objects.filter(phone_number=phone_number).exists()

    @staticmethod
    def create_user(identifier: str = None, email: str = None, phone_number: str = None, **extra_fields) -> User:
        """Create a new user using the UserManager"""
        return User.objects.create_user(
            identifier=identifier,
            email=email,
            phone_number=phone_number,
            **extra_fields
        )

    @staticmethod
    def get_active_users() -> List[User]:
        return list(User.objects.filter(is_active=True, status='ACTIVE'))

    @staticmethod
    def update_last_login(user: User) -> None:
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

    @staticmethod
    def get_by_referral_code(referral_code: str) -> Optional[User]:
        """Get user by referral code"""
        return User.objects.filter(referral_code=referral_code).first()

    @staticmethod
    def count_referrals(user: User) -> int:
        """Count users referred by this user"""
        return User.objects.filter(referred_by=user).count()

    @staticmethod
    def delete_user(user: User) -> None:
        """Delete user account"""
        user.delete()
