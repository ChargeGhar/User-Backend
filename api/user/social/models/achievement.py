from django.db import models
from api.common.models import BaseModel

class Achievement(BaseModel):
    """
    Achievement - Achievements that users can unlock
    """

    class CriteriaTypeChoices(models.TextChoices):
        RENTAL_COUNT = "rental_count", "Rental Count"
        TIMELY_RETURN_COUNT = "timely_return_count", "Timely Return Count"
        REFERRAL_COUNT = "referral_count", "Referral Count"

    class RewardTypeChoices(models.TextChoices):
        POINTS = "points", "Points"

    name = models.CharField(max_length=100)
    description = models.TextField()
    criteria_type = models.CharField(max_length=50, choices=CriteriaTypeChoices.choices)
    criteria_value = models.IntegerField()
    reward_type = models.CharField(max_length=50, choices=RewardTypeChoices.choices)
    reward_value = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "achievements"
        verbose_name = "Achievement"
        verbose_name_plural = "Achievements"

    def __str__(self):
        return self.name
