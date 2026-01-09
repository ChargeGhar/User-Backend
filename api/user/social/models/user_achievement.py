from django.db import models
from api.common.models import BaseModel
from .achievement import Achievement

class UserAchievement(BaseModel):
    """
    UserAchievement - User's progress on achievements

    Two-phase achievement system:
    - is_unlocked: Achievement criteria met (automatic)
    - is_claimed: User acknowledged and claimed rewards (manual)
    """

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="achievements"
    )
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    current_progress = models.IntegerField(default=0)
    is_unlocked = models.BooleanField(default=False)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    is_claimed = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)
    points_awarded = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "user_achievements"
        verbose_name = "User Achievement"
        verbose_name_plural = "User Achievements"
        unique_together = ["user", "achievement"]
        indexes = [
            models.Index(
                fields=["user", "is_unlocked", "is_claimed"], name="idx_user_unlock_claim"
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"
