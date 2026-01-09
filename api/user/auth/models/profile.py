from django.db import models
from api.common.models import BaseModel
from .user import User


class UserProfile(BaseModel):
    """
    UserProfile - Extended user profile information
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    avatar_url = models.URLField(null=True, blank=True)
    is_profile_complete = models.BooleanField(default=False)

    class Meta:
        db_table = "user_profiles"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} Profile"
