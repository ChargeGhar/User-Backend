from django.db import models
from api.common.models import BaseModel


class PaymentMethod(BaseModel):
    """
    PaymentMethod - Available payment gateways
    """
    name = models.CharField(max_length=100)
    gateway = models.CharField(max_length=255)
    icon = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Payment method icon URL or asset path"
    )
    is_active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    supported_currencies = models.JSONField(default=list)

    class Meta:
        db_table = "payment_methods"
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
        ordering = ['name']

    def __str__(self):
        return self.name
