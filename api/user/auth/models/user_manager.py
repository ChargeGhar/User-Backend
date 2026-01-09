from __future__ import annotations

from django.contrib.auth.models import BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager for OTP-based authentication"""
    
    def create_user(self, identifier=None, email=None, phone_number=None, **extra_fields):
        """Create and return a regular user with email or phone"""
        # Handle both old and new calling patterns
        if identifier and not email and not phone_number:
            # Old pattern: create_user(identifier='email@example.com')
            if '@' in identifier:
                email = self.normalize_email(identifier)
                phone_number = None
            else:
                email = None
                phone_number = identifier
        elif not identifier and (email or phone_number):
            # New pattern: create_user(email='email@example.com') or create_user(phone_number='+123')
            if email:
                email = self.normalize_email(email)
            # phone_number is already set
        else:
            raise ValueError('Either identifier or email/phone_number must be set')
        
        if not email and not phone_number:
            raise ValueError('Either email or phone_number must be provided')
        
        user = self.model(
            email=email,
            phone_number=phone_number,
            **extra_fields
        )
        user.save(using=self._db)
        return user
    
    def create_superuser(self, identifier, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', 'ACTIVE')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        user = self.create_user(identifier, **extra_fields)
        
        # Create related objects for admin user
        from api.user.payments.models import Wallet
        from api.admin.models import AdminProfile
        from api.user.points.models import UserPoints
        from .profile import UserProfile
        
        UserProfile.objects.get_or_create(user=user, defaults={'is_profile_complete': False})
        UserPoints.objects.get_or_create(user=user)
        Wallet.objects.get_or_create(user=user, defaults={'currency': 'NPR', 'is_active': True})
        AdminProfile.objects.get_or_create(
            user=user, 
            defaults={
                'role': 'super_admin',
                'created_by': user,
                'is_active': True
            }
        )
        
        return user
