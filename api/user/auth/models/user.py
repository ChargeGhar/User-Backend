from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .user_manager import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with OTP-based authentication
    No password field - authentication via OTP only
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('BANNED', 'Banned'),
        ('INACTIVE', 'Inactive'),
    ]

    # Primary identifier fields
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # Profile fields
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    profile_picture = models.URLField(null=True, blank=True)
    
    # Referral system
    referral_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status and verification
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='ACTIVE')
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    # Django required fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_partner = models.BooleanField(
        default=False,
        help_text='True if user is a partner (Franchise/Vendor) - enables password auth'
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    # Use email or phone as username field
    USERNAME_FIELD = 'email'  # Default, but we'll handle both email and phone
    REQUIRED_FIELDS = []
    
    # Social authentication fields (from migration 0006)
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    apple_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    social_provider = models.CharField(
        max_length=20,
        choices=[
            ('EMAIL', 'Email'),
            ('PHONE', 'Phone'),
            ('GOOGLE', 'Google'),
            ('APPLE', 'Apple')
        ],
        default='EMAIL',
        help_text='Primary authentication method used by the user'
    )
    
    # Social profile data storage
    social_profile_data = models.JSONField(default=dict, blank=True)
    
    # Password field - enabled for admin users, disabled for regular users
    
    class Meta:
        db_table = 'users_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    ('email__isnull', False)
                ) | models.Q(
                    ('phone_number__isnull', False)
                ) | models.Q(
                    ('google_id__isnull', False)
                ) | models.Q(
                    ('apple_id__isnull', False)
                ),
                name='user_must_have_identifier'
            )
        ]
    
    def __str__(self):
        return self.email or self.phone_number or f"User {self.id}"
    
    def get_identifier(self):
        """Get the primary identifier (email or phone)"""
        return self.email or self.phone_number
    
    def clean(self):
        """Validate that user has either email or phone"""
        from django.core.exceptions import ValidationError
        if not self.email and not self.phone_number:
            raise ValidationError('User must have either email or phone number')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def set_password(self, raw_password):
        """Allow password setting for admin users and partners, disable for regular users"""
        if self.is_staff or self.is_superuser or self.is_partner:
            # Allow password for admin users and partners
            super().set_password(raw_password)
        else:
            # Disable password for regular users (OTP-only)
            pass
    
    def check_password(self, raw_password):
        """Allow password checking for admin users and partners, disable for regular users"""
        if self.is_staff or self.is_superuser or self.is_partner:
            # Allow password check for admin users and partners
            return super().check_password(raw_password)
        else:
            # Disable password check for regular users
            return False
    
    def set_unusable_password(self):
        """Allow unusable password setting for admin users and partners"""
        if self.is_staff or self.is_superuser or self.is_partner:
            super().set_unusable_password()
        else:
            pass
    
    def has_usable_password(self):
        """Check if user has usable password (admin users and partners only)"""
        if self.is_staff or self.is_superuser or self.is_partner:
            return super().has_usable_password()
        else:
            return False
