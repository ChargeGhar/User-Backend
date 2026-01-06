from __future__ import annotations
from django.db import models
from api.common.models import BaseModel

class AdminProfile(BaseModel):
    """
    AdminProfile - PowerBank Table
    Admin user profile with role-based permissions
    """
    
    class RoleChoices(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        MODERATOR = 'moderator', 'Moderator'
    
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='admin_profile')
    role = models.CharField(max_length=50, choices=RoleChoices.choices)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_admin_profiles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "admin_profiles"
        verbose_name = "Admin Profile"
        verbose_name_plural = "Admin Profiles"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    @property
    def is_super_admin(self):
        return self.role == self.RoleChoices.SUPER_ADMIN
    
    def can_be_deactivated(self) -> tuple[bool, str]:
        """Check if this admin profile can be deactivated"""
        if self.role == self.RoleChoices.SUPER_ADMIN:
            # Count active super admins
            active_super_admins = AdminProfile.objects.filter(
                role=self.RoleChoices.SUPER_ADMIN,
                is_active=True
            ).count()
            
            if active_super_admins <= 1:
                return False, "Cannot deactivate the last active super admin"
        
        return True, ""
    
    def can_change_role(self, new_role: str, changed_by: 'AdminProfile') -> tuple[bool, str]:
        """Check if role can be changed"""
        # Only super admin can change roles
        if changed_by.role != self.RoleChoices.SUPER_ADMIN:
            return False, "Only super admin can change admin roles"
        
        # Only super admin can create/promote to super admin
        if new_role == self.RoleChoices.SUPER_ADMIN and changed_by.role != self.RoleChoices.SUPER_ADMIN:
            return False, "Only super admin can promote to super admin"
        
        # Can't demote last super admin
        if self.role == self.RoleChoices.SUPER_ADMIN and new_role != self.RoleChoices.SUPER_ADMIN:
            active_super_admins = AdminProfile.objects.filter(
                role=self.RoleChoices.SUPER_ADMIN,
                is_active=True
            ).count()
            
            if active_super_admins <= 1:
                return False, "Cannot demote the last super admin"
        
        return True, ""
