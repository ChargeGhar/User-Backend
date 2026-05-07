from decimal import Decimal
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class LateFeeService:
    """
    Service to handle late fee calculations and configuration management
    """

    CACHE_KEY = "active_late_fee_config"
    CACHE_TIMEOUT_SECONDS = 3600

    @staticmethod
    def get_active_configuration():
        """Get the currently active late fee configuration with caching"""
        config = cache.get(LateFeeService.CACHE_KEY)

        if config is None:
            from api.user.rentals.models.late_fee import LateFeeConfiguration
            config = LateFeeConfiguration.objects.filter(is_active=True).first()
            if config:
                cache.set(
                    LateFeeService.CACHE_KEY,
                    config,
                    timeout=LateFeeService.CACHE_TIMEOUT_SECONDS
                )

        return config

    @staticmethod
    def invalidate_cached_configuration():
        """Clear active configuration cache so changes apply immediately"""
        cache.delete(LateFeeService.CACHE_KEY)

    @staticmethod
    def calculate_late_fee(config, normal_rate_per_minute: Decimal, overdue_minutes: int) -> Decimal:
        """
        Calculate late fee based on provided configuration.
        """
        if not config:
            # Fallback to simple calculation if no config provided
            return normal_rate_per_minute * Decimal('2') * Decimal(str(overdue_minutes))

        # Apply grace period
        effective_overdue_minutes = max(0, overdue_minutes - config.grace_period_minutes)

        if effective_overdue_minutes <= 0:
            return Decimal('0')

        fee = Decimal('0')

        if config.fee_type == 'MULTIPLIER':
            fee = normal_rate_per_minute * config.multiplier * Decimal(str(effective_overdue_minutes))
        elif config.fee_type == 'FLAT_RATE':
            overdue_hours = Decimal(str(effective_overdue_minutes)) / Decimal('60')
            fee = config.flat_rate_per_hour * overdue_hours
        elif config.fee_type == 'COMPOUND':
            multiplier_fee = normal_rate_per_minute * config.multiplier * Decimal(str(effective_overdue_minutes))
            flat_hours = Decimal(str(effective_overdue_minutes)) / Decimal('60')
            flat_fee = config.flat_rate_per_hour * flat_hours
            fee = multiplier_fee + flat_fee
        else:
            logger.warning("Unknown late fee type: %s", config.fee_type)
            return Decimal('0')

        # Apply per-day cap if specified
        if config.max_daily_rate:
            minutes_per_day = 24 * 60
            days_overdue = max(1, (effective_overdue_minutes + minutes_per_day - 1) // minutes_per_day)
            max_fee = config.max_daily_rate * Decimal(str(days_overdue))
            fee = min(fee, max_fee)

        return fee

    @staticmethod
    def get_description(config) -> str:
        """Human-readable description of the fee structure"""
        if not config:
            return "No configuration active"

        if config.fee_type == 'MULTIPLIER':
            return f"{config.multiplier:.1f}x normal rate after {config.grace_period_minutes} minute grace period"
        elif config.fee_type == 'FLAT_RATE':
            return f"NPR {config.flat_rate_per_hour:,.2f} per hour after {config.grace_period_minutes} minute grace period"
        elif config.fee_type == 'COMPOUND':
            return f"{config.multiplier:.1f}x normal rate + NPR {config.flat_rate_per_hour:,.2f} flat rate per hour"
        return "Unknown fee type"
