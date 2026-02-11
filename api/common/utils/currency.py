from __future__ import annotations

from decimal import Decimal


def format_currency(amount: Decimal, currency: str = "NPR") -> str:
    """Format currency amount"""
    return f"{currency} {amount:,.2f}"


def get_points_per_npr(default: int = 10) -> int:
    """Get conversion rate from AppConfig: how many points equal NPR 1."""
    try:
        from api.user.system.services import AppConfigService

        raw = AppConfigService().get_config_cached("POINTS_PER_NPR", str(default))
        rate = int(str(raw))
        return rate if rate > 0 else default
    except Exception:
        return default


def calculate_points_from_amount(amount: Decimal, points_per_unit: int = 10, unit_amount: Decimal = Decimal('100')) -> int:
    """Calculate points based on amount (default: 10 points per NPR 100)"""
    if amount <= 0:
        return 0
    return int((amount / unit_amount) * points_per_unit)


def convert_points_to_amount(points: int, points_per_unit: int | None = None, unit_amount: Decimal = Decimal('1')) -> Decimal:
    """Convert points to monetary amount (default from AppConfig POINTS_PER_NPR)."""
    if points <= 0:
        return Decimal('0')
    rate = points_per_unit if points_per_unit is not None else get_points_per_npr()
    if rate <= 0:
        rate = 10
    return (Decimal(points) / Decimal(rate)) * unit_amount
