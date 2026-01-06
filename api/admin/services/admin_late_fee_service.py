"""
Late Fee Configuration Service
============================================================

Service for managing late fee configurations in admin panel.
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
from decimal import Decimal
from django.db import transaction

from api.common.services.base import CRUDService, ServiceException
from api.rentals.models.late_fee import LateFeeConfiguration
from api.common.utils.helpers import paginate_queryset


class LateFeeConfigurationService(CRUDService):
    """Service for late fee configuration management"""
    
    model = LateFeeConfiguration
    
    def get_all_configurations(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get all late fee configurations with optional filtering and pagination
        
        Args:
            filters: Optional filters including:
                - is_active: Filter by active status (bool)
                - fee_type: Filter by fee type (str)
                - search: Search in name (str)
                - page: Page number (int)
                - page_size: Items per page (int)
        
        Returns:
            Dict containing configurations list and pagination info
        """
        try:
            queryset = LateFeeConfiguration.objects.all()
            
            # Apply filters
            if filters:
                # Filter by active status
                if 'is_active' in filters and filters['is_active'] is not None:
                    queryset = queryset.filter(is_active=filters['is_active'])
                
                # Filter by fee type
                if filters.get('fee_type'):
                    queryset = queryset.filter(fee_type=filters['fee_type'])
                
                # Search in name
                if filters.get('search'):
                    queryset = queryset.filter(name__icontains=filters['search'])
            
            # Order by active first, then by creation date
            queryset = queryset.order_by('-is_active', '-created_at')
            
            # Pagination
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20
            
            paginated_data = paginate_queryset(queryset, page, page_size)
            
            # Add summary
            active_count = LateFeeConfiguration.objects.filter(is_active=True).count()
            total_count = LateFeeConfiguration.objects.count()
            
            paginated_data['summary'] = {
                'total_configurations': total_count,
                'active_configurations': active_count,
                'inactive_configurations': total_count - active_count
            }
            
            return paginated_data
            
        except Exception as e:
            self.handle_service_error(e, "Failed to retrieve late fee configurations")
    
    def get_configuration_by_id(self, config_id: str) -> LateFeeConfiguration:
        """
        Get a specific late fee configuration by ID
        
        Args:
            config_id: UUID of the configuration
            
        Returns:
            LateFeeConfiguration instance
            
        Raises:
            ServiceException: If configuration not found
        """
        try:
            config = LateFeeConfiguration.objects.get(id=config_id)
            self.log_info(f"Retrieved late fee configuration: {config.name} (ID: {config_id})")
            return config
            
        except LateFeeConfiguration.DoesNotExist:
            raise ServiceException(
                detail=f"Late fee configuration with ID {config_id} not found",
                code="configuration_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, f"Failed to retrieve configuration {config_id}")
    
    def get_active_configuration(self) -> Optional[LateFeeConfiguration]:
        """
        Get the currently active late fee configuration
        
        Returns:
            Active LateFeeConfiguration instance or None if no active configuration
        """
        try:
            config = LateFeeConfiguration.objects.filter(is_active=True).first()
            if config:
                self.log_info(f"Active late fee configuration: {config.name}")
            else:
                self.log_warning("No active late fee configuration found")
            return config
            
        except Exception as e:
            self.handle_service_error(e, "Failed to retrieve active configuration")
    
    @transaction.atomic
    def create_configuration(
        self,
        name: str,
        fee_type: str,
        multiplier: Decimal = Decimal('2.0'),
        flat_rate_per_hour: Decimal = Decimal('0'),
        grace_period_minutes: int = 0,
        max_daily_rate: Optional[Decimal] = None,
        is_active: bool = True,
        applicable_package_types: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        admin_user = None
    ) -> LateFeeConfiguration:
        """
        Create a new late fee configuration
        
        Args:
            name: Configuration name
            fee_type: Type of fee calculation (MULTIPLIER, FLAT_RATE, COMPOUND)
            multiplier: Multiplier for rate calculation
            flat_rate_per_hour: Flat rate per hour
            grace_period_minutes: Grace period before charges apply
            max_daily_rate: Maximum fee per day (optional)
            is_active: Whether configuration is active
            applicable_package_types: List of package types this applies to
            metadata: Additional metadata
            admin_user: Admin user creating the configuration
            
        Returns:
            Created LateFeeConfiguration instance
        """
        try:
            # If setting as active, deactivate all others
            if is_active:
                self._deactivate_all_configurations()
            
            # Create configuration
            config = LateFeeConfiguration.objects.create(
                name=name,
                fee_type=fee_type,
                multiplier=multiplier,
                flat_rate_per_hour=flat_rate_per_hour,
                grace_period_minutes=grace_period_minutes,
                max_daily_rate=max_daily_rate,
                is_active=is_active,
                applicable_package_types=applicable_package_types or [],
                metadata=metadata or {}
            )
            
            self.log_info(
                f"Late fee configuration created: {config.name} (Type: {fee_type}, Active: {is_active})",
                extra={'admin_user': admin_user.username if admin_user else 'system'}
            )
            
            # Log admin action
            if admin_user:
                self._log_admin_action(
                    admin_user=admin_user,
                    action='create_late_fee_config',
                    details={
                        'config_id': str(config.id),
                        'config_name': config.name,
                        'fee_type': fee_type,
                        'is_active': is_active
                    }
                )
            
            return config
            
        except Exception as e:
            self.handle_service_error(e, "Failed to create late fee configuration")
    
    @transaction.atomic
    def update_configuration(
        self,
        config_id: str,
        admin_user = None,
        **update_fields
    ) -> LateFeeConfiguration:
        """
        Update an existing late fee configuration
        
        Args:
            config_id: UUID of configuration to update
            admin_user: Admin user performing the update
            **update_fields: Fields to update (name, fee_type, multiplier, etc.)
            
        Returns:
            Updated LateFeeConfiguration instance
        """
        try:
            config = self.get_configuration_by_id(config_id)
            
            # Track changes for logging
            changes = {}
            
            # Update fields
            for field, value in update_fields.items():
                if value is not None and hasattr(config, field):
                    old_value = getattr(config, field)
                    if old_value != value:
                        setattr(config, field, value)
                        changes[field] = {'old': str(old_value), 'new': str(value)}
            
            # If activating this config, deactivate others
            if update_fields.get('is_active') is True:
                self._deactivate_all_configurations(exclude_id=config_id)
            
            config.save()
            
            self.log_info(
                f"Late fee configuration updated: {config.name} (Changes: {len(changes)})",
                extra={
                    'admin_user': admin_user.username if admin_user else 'system',
                    'changes': changes
                }
            )
            
            # Log admin action
            if admin_user:
                self._log_admin_action(
                    admin_user=admin_user,
                    action='update_late_fee_config',
                    details={
                        'config_id': str(config.id),
                        'config_name': config.name,
                        'changes': changes
                    }
                )
            
            return config
            
        except Exception as e:
            self.handle_service_error(e, f"Failed to update configuration {config_id}")
    
    @transaction.atomic
    def activate_configuration(
        self,
        config_id: str,
        deactivate_others: bool = True,
        admin_user = None
    ) -> LateFeeConfiguration:
        """
        Activate a late fee configuration
        
        Args:
            config_id: UUID of configuration to activate
            deactivate_others: Whether to deactivate other configurations
            admin_user: Admin user performing the activation
            
        Returns:
            Activated LateFeeConfiguration instance
        """
        try:
            config = self.get_configuration_by_id(config_id)
            
            if config.is_active:
                self.log_info(f"Configuration {config.name} is already active")
                return config
            
            # Deactivate others if requested
            if deactivate_others:
                self._deactivate_all_configurations(exclude_id=config_id)
            
            config.is_active = True
            config.save()
            
            self.log_info(
                f"Late fee configuration activated: {config.name}",
                extra={'admin_user': admin_user.username if admin_user else 'system'}
            )
            
            # Log admin action
            if admin_user:
                self._log_admin_action(
                    admin_user=admin_user,
                    action='activate_late_fee_config',
                    details={
                        'config_id': str(config.id),
                        'config_name': config.name
                    }
                )
            
            return config
            
        except Exception as e:
            self.handle_service_error(e, f"Failed to activate configuration {config_id}")
    
    @transaction.atomic
    def deactivate_configuration(
        self,
        config_id: str,
        admin_user = None
    ) -> LateFeeConfiguration:
        """
        Deactivate a late fee configuration
        
        Args:
            config_id: UUID of configuration to deactivate
            admin_user: Admin user performing the deactivation
            
        Returns:
            Deactivated LateFeeConfiguration instance
        """
        try:
            config = self.get_configuration_by_id(config_id)
            
            if not config.is_active:
                self.log_info(f"Configuration {config.name} is already inactive")
                return config
            
            config.is_active = False
            config.save()
            
            self.log_warning(
                f"Late fee configuration deactivated: {config.name}. No active configuration exists!",
                extra={'admin_user': admin_user.username if admin_user else 'system'}
            )
            
            # Log admin action
            if admin_user:
                self._log_admin_action(
                    admin_user=admin_user,
                    action='deactivate_late_fee_config',
                    details={
                        'config_id': str(config.id),
                        'config_name': config.name
                    }
                )
            
            return config
            
        except Exception as e:
            self.handle_service_error(e, f"Failed to deactivate configuration {config_id}")
    
    @transaction.atomic
    def delete_configuration(
        self,
        config_id: str,
        admin_user = None
    ) -> str:
        """
        Delete a late fee configuration
        
        Args:
            config_id: UUID of configuration to delete
            admin_user: Admin user performing the deletion
            
        Returns:
            Name of deleted configuration
            
        Raises:
            ServiceException: If trying to delete active configuration
        """
        try:
            config = self.get_configuration_by_id(config_id)
            config_name = config.name
            
            # Prevent deletion of active configuration
            if config.is_active:
                raise ServiceException(
                    detail="Cannot delete active late fee configuration. Please deactivate it first.",
                    code="cannot_delete_active_config"
                )
            
            config.delete()
            
            self.log_info(
                f"Late fee configuration deleted: {config_name}",
                extra={'admin_user': admin_user.username if admin_user else 'system'}
            )
            
            # Log admin action
            if admin_user:
                self._log_admin_action(
                    admin_user=admin_user,
                    action='delete_late_fee_config',
                    details={
                        'config_id': str(config_id),
                        'config_name': config_name
                    }
                )
            
            return config_name
            
        except Exception as e:
            self.handle_service_error(e, f"Failed to delete configuration {config_id}")
    
    def test_calculation(
        self,
        config_id: str,
        normal_rate_per_minute: Decimal,
        overdue_minutes: int
    ) -> Dict[str, Any]:
        """
        Test late fee calculation for a configuration
        
        Args:
            config_id: UUID of configuration to test
            normal_rate_per_minute: Normal rental rate per minute
            overdue_minutes: Number of minutes overdue
            
        Returns:
            Dict with calculation results and breakdown
        """
        try:
            config = self.get_configuration_by_id(config_id)
            
            # Calculate late fee
            late_fee = config.calculate_late_fee(normal_rate_per_minute, overdue_minutes)
            
            # Calculate breakdown
            effective_overdue = max(0, overdue_minutes - config.grace_period_minutes)
            
            breakdown = {
                'configuration_name': config.name,
                'fee_type': config.fee_type,
                'normal_rate_per_minute': float(normal_rate_per_minute),
                'overdue_minutes': overdue_minutes,
                'grace_period_minutes': config.grace_period_minutes,
                'effective_overdue_minutes': effective_overdue,
                'calculated_late_fee': float(late_fee),
                'description': config.get_description()
            }
            
            # Add type-specific details
            if config.fee_type == 'MULTIPLIER':
                breakdown['multiplier'] = float(config.multiplier)
                breakdown['calculation'] = f"{effective_overdue} min × {normal_rate_per_minute} NPR/min × {config.multiplier}x"
            
            elif config.fee_type == 'FLAT_RATE':
                overdue_hours = effective_overdue / 60
                breakdown['flat_rate_per_hour'] = float(config.flat_rate_per_hour)
                breakdown['overdue_hours'] = round(overdue_hours, 2)
                breakdown['calculation'] = f"{overdue_hours:.2f} hrs × {config.flat_rate_per_hour} NPR/hr"
            
            elif config.fee_type == 'COMPOUND':
                breakdown['multiplier'] = float(config.multiplier)
                breakdown['flat_rate_per_hour'] = float(config.flat_rate_per_hour)
                overdue_hours = effective_overdue / 60
                breakdown['overdue_hours'] = round(overdue_hours, 2)
                
                multiplier_fee = normal_rate_per_minute * config.multiplier * Decimal(str(effective_overdue))
                flat_fee = config.flat_rate_per_hour * Decimal(str(overdue_hours))
                
                breakdown['multiplier_component'] = float(multiplier_fee)
                breakdown['flat_rate_component'] = float(flat_fee)
                breakdown['calculation'] = (
                    f"({effective_overdue} min × {normal_rate_per_minute} NPR/min × {config.multiplier}x) + "
                    f"({overdue_hours:.2f} hrs × {config.flat_rate_per_hour} NPR/hr)"
                )
            
            # Add cap info if applicable
            if config.max_daily_rate:
                breakdown['max_daily_rate'] = float(config.max_daily_rate)
                breakdown['cap_applied'] = late_fee < (normal_rate_per_minute * Decimal(str(effective_overdue)) * config.multiplier)
            
            self.log_info(f"Late fee calculation test: {config.name} → NPR {late_fee}")
            
            return breakdown
            
        except Exception as e:
            self.handle_service_error(e, f"Failed to test calculation for configuration {config_id}")
    
    # Private helper methods
    
    def _deactivate_all_configurations(self, exclude_id: Optional[str] = None) -> int:
        """Deactivate all configurations except the specified one"""
        queryset = LateFeeConfiguration.objects.filter(is_active=True)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        count = queryset.update(is_active=False)
        
        if count > 0:
            self.log_info(f"Deactivated {count} late fee configuration(s)")
        
        return count
    
    def _log_admin_action(self, admin_user, action: str, details: Dict[str, Any]) -> None:
        """Log admin action for audit trail"""
        try:
            from api.admin.models import AdminProfile as AdminActionLog
            
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action=action,
                target_model='LateFeeConfiguration',
                target_id=details.get('config_id'),
                details=details,
                ip_address=None,  # Can be added if available
                user_agent=None   # Can be added if available
            )
        except Exception as e:
            self.log_error(f"Failed to log admin action: {str(e)}")
