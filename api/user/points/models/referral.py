from django.db import models
from api.common.models import BaseModel

class Referral(BaseModel):
    """
    Referral - Referral tracking and rewards
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    ]

    inviter = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='sent_referrals')
    invitee = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='received_referrals')
    referral_code = models.CharField(max_length=10)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    inviter_points_awarded = models.IntegerField(default=0)
    invitee_points_awarded = models.IntegerField(default=0)
    first_rental_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "referrals"
        verbose_name = "Referral"
        verbose_name_plural = "Referrals"

    def __str__(self):
        return f"{self.inviter.username} -> {self.invitee.username}"
