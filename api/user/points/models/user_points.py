from django.db import models
from api.common.models import BaseModel

class UserPoints(BaseModel):
    """
    UserPoints - User's points balance
    Moved from users.UserPoints to points.UserPoints for centralization
    """
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='points')
    current_points = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_points"
        verbose_name = "User Points"
        verbose_name_plural = "User Points"

    def __str__(self):
        return f"{self.user.username or self.user.id} - {self.current_points} points"
