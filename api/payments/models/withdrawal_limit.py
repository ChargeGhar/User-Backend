from django.db import models
from api.common.models import BaseModel


class WithdrawalLimit(BaseModel):
    """
    WithdrawalLimit - Track user withdrawal limits
    """
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='withdrawal_limit')
    daily_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monthly_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_daily_reset = models.DateField(auto_now_add=True)
    last_monthly_reset = models.DateField(auto_now_add=True)

    class Meta:
        db_table = "withdrawal_limits"
        verbose_name = "Withdrawal Limit"
        verbose_name_plural = "Withdrawal Limits"

    def __str__(self):
        return f"{self.user.username} - Daily: {self.daily_withdrawn}, Monthly: {self.monthly_withdrawn}"
