from __future__ import annotations

from decimal import Decimal


def format_currency(amount: Decimal, currency: str = "NPR") -> str:
    """Format currency amount"""
    return f"{currency} {amount:,.2f}"


def calculate_points_from_amount(amount: Decimal, points_per_unit: int = 10, unit_amount: Decimal = Decimal('100')) -> int:
    """Calculate points based on amount (default: 10 points per NPR 100)"""
    if amount <= 0:
        return 0
    return int((amount / unit_amount) * points_per_unit)


def convert_points_to_amount(points: int, points_per_unit: int = 10, unit_amount: Decimal = Decimal('1')) -> Decimal:
    """Convert points to monetary amount (default: 10 points = NPR 1)"""
    if points <= 0:
        return Decimal('0')
    return Decimal(points / points_per_unit) * unit_amount
