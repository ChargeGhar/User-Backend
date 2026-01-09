"""
Service for admin achievement management
============================================================

This module contains service classes for admin achievement management operations.
Wraps social app achievement services with admin-specific features.

Created: 2025-11-11
"""
from __future__ import annotations

from typing import Dict, Any, List
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.utils import timezone

from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.admin.models import AdminActionLog
from api.user.social.models import Achievement, UserAchievement


class AdminAchievementService(CRUDService):
    """Service for admin achievement management"""
    model = Achievement
    
    @transaction.atomic
    def create_achievement(
        self,
        name: str,
        description: str,
        criteria_type: str,
        criteria_value: int,
        reward_type: str,
        reward_value: int,
        admin_user
    ) -> Achievement:
        """
        Create new achievement
        
        Args:
            name: Achievement name
            description: Achievement description
            criteria_type: Type of criteria (rental_count, timely_return_count, referral_count)
            criteria_value: Value to achieve
            reward_type: Type of reward (points)
            reward_value: Reward value
            admin_user: Admin user creating the achievement
            
        Returns:
            Created Achievement object
        """
        try:
            # Check for duplicate name
            if Achievement.objects.filter(name=name).exists():
                raise ServiceException(
                    detail=f"Achievement with name '{name}' already exists",
                    code="achievement_already_exists",
                    status_code=409,
                    context={'existing_name': name},
                    user_message=f"An achievement with the name '{name}' already exists. Please use a different name."
                )
            
            # Create achievement
            achievement = Achievement.objects.create(
                name=name,
                description=description,
                criteria_type=criteria_type,
                criteria_value=criteria_value,
                reward_type=reward_type,
                reward_value=reward_value,
                is_active=True
            )
            
            # Log admin action
            self._log_admin_action(
                admin_user=admin_user,
                action_type='CREATE_ACHIEVEMENT',
                target_model='Achievement',
                target_id=str(achievement.id),
                changes={
                    'name': name,
                    'description': description,
                    'criteria_type': criteria_type,
                    'criteria_value': criteria_value,
                    'reward_type': reward_type,
                    'reward_value': reward_value
                },
                description=f"Created achievement: {name}"
            )
            
            self.log_info(f"Achievement created: {name} by admin {admin_user.username}")
            return achievement
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to create achievement")
    
    @transaction.atomic
    def update_achievement(
        self,
        achievement_id: str,
        update_data: Dict[str, Any],
        admin_user
    ) -> Achievement:
        """
        Update existing achievement
        
        Args:
            achievement_id: Achievement ID to update
            update_data: Dict with fields to update
            admin_user: Admin user updating the achievement
            
        Returns:
            Updated Achievement object
        """
        try:
            # Get achievement
            achievement = Achievement.objects.get(id=achievement_id)
            
            # Track changes
            changes = {}
            old_values = {}
            
            # Update allowed fields
            allowed_fields = [
                'name', 'description', 'criteria_type', 'criteria_value',
                'reward_type', 'reward_value', 'is_active'
            ]
            
            for field in allowed_fields:
                if field in update_data:
                    old_value = getattr(achievement, field)
                    new_value = update_data[field]
                    
                    if old_value != new_value:
                        old_values[field] = old_value
                        setattr(achievement, field, new_value)
                        changes[field] = new_value
            
            # Check if name already exists (if name is being changed)
            if 'name' in changes and Achievement.objects.filter(
                name=changes['name']
            ).exclude(id=achievement_id).exists():
                raise ServiceException(
                    detail=f"Achievement with name '{changes['name']}' already exists",
                    code="achievement_name_exists",
                    status_code=409,
                    user_message=f"An achievement with the name '{changes['name']}' already exists."
                )
            
            if changes:
                achievement.save()
                
                # Log admin action
                self._log_admin_action(
                    admin_user=admin_user,
                    action_type='UPDATE_ACHIEVEMENT',
                    target_model='Achievement',
                    target_id=str(achievement.id),
                    changes={
                        'old_values': old_values,
                        'new_values': changes
                    },
                    description=f"Updated achievement: {achievement.name}"
                )
                
                self.log_info(
                    f"Achievement {achievement.name} updated by admin {admin_user.username}"
                )
            
            return achievement
            
        except Achievement.DoesNotExist:
            raise ServiceException(
                detail="Achievement not found",
                code="achievement_not_found",
                status_code=404,
                user_message="The specified achievement does not exist"
            )
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to update achievement")
    
    @transaction.atomic
    def delete_achievement(
        self,
        achievement_id: str,
        admin_user
    ) -> Dict[str, Any]:
        """
        Delete achievement (soft delete by deactivating)
        
        Args:
            achievement_id: Achievement ID to delete
            admin_user: Admin user deleting the achievement
            
        Returns:
            Dict with deletion details
        """
        try:
            # Get achievement
            achievement = Achievement.objects.get(id=achievement_id)
            achievement_name = achievement.name
            
            # Check if achievement has any unlocked instances
            unlocked_count = UserAchievement.objects.filter(
                achievement=achievement,
                is_unlocked=True
            ).count()
            
            # Soft delete by deactivating
            achievement.is_active = False
            achievement.save(update_fields=['is_active', 'updated_at'])
            
            # Log admin action
            self._log_admin_action(
                admin_user=admin_user,
                action_type='DELETE_ACHIEVEMENT',
                target_model='Achievement',
                target_id=str(achievement.id),
                changes={
                    'is_active': False,
                    'unlocked_count': unlocked_count
                },
                description=f"Deleted (deactivated) achievement: {achievement_name}"
            )
            
            self.log_info(
                f"Achievement {achievement_name} deleted by admin {admin_user.username}"
            )
            
            return {
                'achievement_id': str(achievement.id),
                'achievement_name': achievement_name,
                'unlocked_count': unlocked_count,
                'message': f'Achievement {achievement_name} has been deactivated successfully'
            }
            
        except Achievement.DoesNotExist:
            raise ServiceException(
                detail="Achievement not found",
                code="achievement_not_found",
                status_code=404,
                user_message="The specified achievement does not exist"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to delete achievement")
    
    def get_all_achievements(
        self,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get all achievements with optional filters
        
        Args:
            filters: Optional filters (criteria_type, is_active, search, pagination)
            
        Returns:
            Paginated list of achievements
        """
        try:
            # Base queryset with stats
            queryset = Achievement.objects.annotate(
                total_unlocked=Count(
                    'userachievement',
                    filter=Q(userachievement__is_unlocked=True)
                ),
                total_claimed=Count(
                    'userachievement',
                    filter=Q(userachievement__is_claimed=True)
                ),
                total_users_progress=Count('userachievement', distinct=True)
            )
            
            # Apply filters
            if filters:
                # Criteria type filter
                if filters.get('criteria_type'):
                    queryset = queryset.filter(criteria_type=filters['criteria_type'])
                
                # Active/inactive filter
                if filters.get('is_active') is not None:
                    queryset = queryset.filter(is_active=filters['is_active'])
                
                # Search filter
                if filters.get('search'):
                    search_term = filters['search']
                    queryset = queryset.filter(
                        Q(name__icontains=search_term) |
                        Q(description__icontains=search_term)
                    )
            
            # Order by creation date
            queryset = queryset.order_by('-created_at')
            
            # Pagination
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20
            
            return paginate_queryset(queryset, page, page_size)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get achievements")
    
    def get_achievement_analytics(self) -> Dict[str, Any]:
        """
        Get achievement analytics
        
        Returns:
            Dict with achievement analytics
        """
        try:
            # Total achievements
            total_achievements = Achievement.objects.count()
            active_achievements = Achievement.objects.filter(is_active=True).count()
            
            # User achievement statistics
            total_unlocked = UserAchievement.objects.filter(is_unlocked=True).count()
            total_claimed = UserAchievement.objects.filter(is_claimed=True).count()
            pending_claims = UserAchievement.objects.filter(
                is_unlocked=True,
                is_claimed=False
            ).count()
            
            # Points awarded through achievements
            total_points_awarded = UserAchievement.objects.filter(
                is_claimed=True
            ).aggregate(
                total=Sum('points_awarded')
            )['total'] or 0
            
            # Most unlocked achievements
            most_unlocked = Achievement.objects.annotate(
                unlock_count=Count(
                    'userachievement',
                    filter=Q(userachievement__is_unlocked=True)
                )
            ).filter(unlock_count__gt=0).order_by('-unlock_count')[:5]
            
            most_unlocked_data = [
                {
                    'achievement_id': str(ach.id),
                    'name': ach.name,
                    'unlock_count': ach.unlock_count,
                    'reward_value': ach.reward_value
                }
                for ach in most_unlocked
            ]
            
            # Achievement completion rates by criteria type
            completion_by_type = Achievement.objects.values('criteria_type').annotate(
                total_achievements=Count('id'),
                total_unlocked=Count(
                    'userachievement',
                    filter=Q(userachievement__is_unlocked=True)
                ),
                total_claimed=Count(
                    'userachievement',
                    filter=Q(userachievement__is_claimed=True)
                )
            )
            
            # Calculate rates
            for item in completion_by_type:
                if item['total_achievements'] > 0:
                    item['unlock_rate'] = round(
                        (item['total_unlocked'] / item['total_achievements']) * 100, 2
                    )
                    item['claim_rate'] = round(
                        (item['total_claimed'] / item['total_achievements']) * 100, 2
                    )
                else:
                    item['unlock_rate'] = 0
                    item['claim_rate'] = 0
            
            return {
                'total_achievements': total_achievements,
                'active_achievements': active_achievements,
                'inactive_achievements': total_achievements - active_achievements,
                'user_achievements': {
                    'total_unlocked': total_unlocked,
                    'total_claimed': total_claimed,
                    'pending_claims': pending_claims,
                    'claim_rate': round((total_claimed / total_unlocked * 100), 2) if total_unlocked > 0 else 0
                },
                'total_points_awarded': total_points_awarded,
                'most_unlocked_achievements': most_unlocked_data,
                'completion_by_criteria_type': list(completion_by_type)
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get achievement analytics")
    
    def _log_admin_action(
        self,
        admin_user,
        action_type: str,
        target_model: str,
        target_id: str,
        changes: Dict[str, Any],
        description: str = ""
    ) -> None:
        """Log admin action for audit trail"""
        try:
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type=action_type,
                target_model=target_model,
                target_id=target_id,
                changes=changes,
                description=description,
                ip_address="127.0.0.1",  # Should be passed from request
                user_agent="Admin Panel"  # Should be passed from request
            )
        except Exception as e:
            self.log_error(f"Failed to log admin action: {str(e)}")
