from django.db import models
from api.common.models import BaseModel

class UserLeaderboard(BaseModel):
    """
    UserLeaderboard - User rankings and statistics
    """

    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="leaderboard"
    )
    rank = models.IntegerField()
    total_rentals = models.IntegerField(default=0)
    total_points_earned = models.IntegerField(default=0)
    referrals_count = models.IntegerField(default=0)
    timely_returns = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_leaderboard"
        verbose_name = "User Leaderboard"
        verbose_name_plural = "User Leaderboard"
        ordering = ["rank"]

    def __str__(self):
        return f"#{self.rank} - {self.user.username}"
