from django.db import models
from api.common.models import BaseModel

class ContactInfo(BaseModel):
    """
    ContactInfo - Contact information like phone, email, address
    """
    
    class InfoTypeChoices(models.TextChoices):
        PHONE = 'phone', 'Phone'
        EMAIL = 'email', 'Email'
        ADDRESS = 'address', 'Address'
        SUPPORT_HOURS = 'support_hours', 'Support Hours'
    
    info_type = models.CharField(max_length=255, choices=InfoTypeChoices.choices, unique=True)
    label = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='updated_contact_info')
    
    class Meta:
        db_table = "contact_info"
        verbose_name = "Contact Info"
        verbose_name_plural = "Contact Info"
    
    def __str__(self):
        return f"{self.get_info_type_display()}: {self.value}"
