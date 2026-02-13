from django.db import models
from api.common.models import BaseModel
from .user import User


class UserKYC(BaseModel):
    """
    UserKYC - KYC verification documents
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='kyc')
    document_type = models.CharField(max_length=50, default='CITIZENSHIP')
    document_number = models.CharField(max_length=100)
    document_front_url = models.URLField()
    font_face_url = models.URLField(null=True, blank=True)
    document_back_url = models.URLField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_kycs')
    rejection_reason = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "user_kyc"
        verbose_name = "User KYC"
        verbose_name_plural = "User KYCs"

    def __str__(self):
        return f"{self.user.username} KYC - {self.status}"
