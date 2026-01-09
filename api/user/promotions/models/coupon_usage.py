from django.db import models
from api.common.models import BaseModel
from .coupon import Coupon

class CouponUsage(BaseModel):
    """
    CouponUsage - Track coupon usage by users
    """
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='coupon_usages')
    points_awarded = models.IntegerField()
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "coupon_usages"
        verbose_name = "Coupon Usage"
        verbose_name_plural = "Coupon Usages"
        unique_together = ['coupon', 'user']
    
    def __str__(self):
        return f"{self.user.username} used {self.coupon.code}"
