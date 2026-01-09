"""User identifier helper utilities"""
from api.user.auth.models import User


def is_email(identifier: str) -> bool:
    """Check if identifier is an email"""
    return '@' in identifier


def check_user_exists(identifier: str) -> bool:
    """Check if user exists by identifier"""
    if is_email(identifier):
        return User.objects.filter(email=identifier).exists()
    return User.objects.filter(phone_number=identifier).exists()


def get_user_by_identifier(identifier: str) -> User:
    """Get user by identifier"""
    if is_email(identifier):
        return User.objects.get(email=identifier)
    return User.objects.get(phone_number=identifier)
