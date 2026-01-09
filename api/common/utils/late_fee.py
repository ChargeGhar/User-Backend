from __future__ import annotations

from decimal import Decimal
from django.core.cache import cache


def get_late_fee_configuration():
    """Get the currently active late fee configuration"""
    from api.user.rentals.models.late_fee import LateFeeConfiguration
    try:
        return LateFeeConfiguration.objects.filter(is_active=True).first()
    except Exception:
        return None


def calculate_late_fee_amount(normal_rate_per_minute: Decimal, overdue_minutes: int,
                             package_type: str = None) -> Decimal:
    """Calculate late fee amount using active configuration"""
    cache_key = f"late_fee_config_{package_type or 'default'}"
    config = cache.get(cache_key)

    if config is None:
        config = get_late_fee_configuration()

        if config is None:
            return normal_rate_per_minute * Decimal('2') * Decimal(str(overdue_minutes))

        cache.set(cache_key, config, timeout=3600)

    return config.calculate_late_fee(normal_rate_per_minute, overdue_minutes)


def calculate_overdue_minutes(rental) -> int:
    """Calculate overdue minutes for a rental"""
    if not rental.ended_at or not rental.due_at:
        return 0

    if rental.ended_at <= rental.due_at:
        return 0

    overdue_duration = rental.ended_at - rental.due_at
    overdue_minutes = int(overdue_duration.total_seconds() / 60)

    return max(0, overdue_minutes)


def get_package_rate_per_minute(package) -> Decimal:
    """Get package rate per minute"""
    return package.price / Decimal(str(package.duration_minutes))
