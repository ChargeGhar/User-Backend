from django.db import models
from api.common.models import BaseModel

class PointsTransaction(BaseModel):
    """
    PointsTransaction - Points earning and spending history
    """
    TRANSACTION_TYPE_CHOICES = [
        ('EARNED', 'Earned'),
        ('SPENT', 'Spent'),
        ('ADJUSTMENT', 'Adjustment'),
    ]

    SOURCE_CHOICES = [
        ('SIGNUP', 'Signup'),
        ('REFERRAL_INVITER', 'Referral Inviter'),
        ('REFERRAL_INVITEE', 'Referral Invitee'),
        ('TOPUP', 'Top Up'),
        ('RENTAL_COMPLETE', 'Rental Complete'),
        ('TIMELY_RETURN', 'Timely Return'),
        ('COUPON', 'Coupon'),
        ('RENTAL_PAYMENT', 'Rental Payment'),
        ('ADMIN_ADJUSTMENT', 'Admin Adjustment'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='points_transactions')
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    points = models.IntegerField()
    balance_before = models.IntegerField()
    balance_after = models.IntegerField()
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict)
    related_rental = models.ForeignKey('rentals.Rental', on_delete=models.SET_NULL, null=True, blank=True)
    related_referral = models.ForeignKey('points.Referral', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "points_transactions"
        verbose_name = "Points Transaction"
        verbose_name_plural = "Points Transactions"

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} {self.points}"
