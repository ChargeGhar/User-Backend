from __future__ import annotations

from decimal import Decimal


def get_late_fee_configuration():
    """Get the currently active late fee configuration"""
    from api.user.rentals.services.late_fee_service import LateFeeService
    return LateFeeService.get_active_configuration()


def calculate_late_fee_amount(normal_rate_per_minute: Decimal, overdue_minutes: int,
                             package_type: str = None) -> Decimal:
    """Calculate late fee amount using active configuration."""
    # package_type kept for backward compatibility of function signature.
    from api.user.rentals.services.late_fee_service import LateFeeService
    config = LateFeeService.get_active_configuration()
    return LateFeeService.calculate_late_fee(config, normal_rate_per_minute, overdue_minutes)


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
