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
    related_referral = models.ForeignKey('Referral', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "points_transactions"
        verbose_name = "Points Transaction"
        verbose_name_plural = "Points Transactions"

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} {self.points}"


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


