from typing import Optional
from api.user.auth.models import UserProfile, UserKYC

class ProfileRepository:
    """Repository for UserProfile and UserKYC data operations"""
    
    @staticmethod
    def get_by_user_id(user_id: str) -> Optional[UserProfile]:
        try:
            return UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return None

    @staticmethod
    def create_profile(user, **kwargs) -> UserProfile:
        return UserProfile.objects.create(user=user, **kwargs)

    @staticmethod
    def update_profile(profile: UserProfile, **kwargs) -> UserProfile:
        for key, value in kwargs.items():
            setattr(profile, key, value)
        profile.save()
        return profile

    @staticmethod
    def get_kyc_by_user_id(user_id: str) -> Optional[UserKYC]:
        try:
            return UserKYC.objects.get(user_id=user_id)
        except UserKYC.DoesNotExist:
            return None

    @staticmethod
    def create_or_update_kyc(user, **kwargs) -> tuple[UserKYC, bool]:
        """Create or update KYC record"""
        return UserKYC.objects.update_or_create(user=user, defaults=kwargs)

    @staticmethod
    def update_kyc(kyc: UserKYC, **kwargs) -> UserKYC:
        for key, value in kwargs.items():
            setattr(kyc, key, value)
        kyc.save()
        return kyc
