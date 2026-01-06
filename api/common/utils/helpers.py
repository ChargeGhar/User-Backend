"""
Common utility helpers module.

This module re-exports utilities from domain-specific files for backward compatibility.
For new code, prefer importing from specific modules:
    - codes.py: Code generation (generate_random_code, generate_transaction_id, etc.)
    - pagination.py: Pagination utilities (paginate_queryset)
    - validation.py: Validation helpers (validate_phone_number, mask_sensitive_data)
    - geo.py: Geographic calculations (calculate_distance)
    - currency.py: Currency/points utilities (format_currency, calculate_points_from_amount)
    - response.py: Response helpers (create_success_response, create_error_response)
    - late_fee.py: Late fee calculations (calculate_late_fee_amount, calculate_overdue_minutes)
"""
from __future__ import annotations

from .codes import (
    generate_random_code,
    generate_unique_code,
    generate_transaction_id,
    generate_rental_code,
)
from .pagination import paginate_queryset
from .validation import validate_phone_number, mask_sensitive_data
from .geo import calculate_distance
from .currency import format_currency, calculate_points_from_amount, convert_points_to_amount
from .response import create_success_response, create_error_response, get_client_ip
from .late_fee import (
    get_late_fee_configuration,
    calculate_late_fee_amount,
    calculate_overdue_minutes,
    get_package_rate_per_minute,
)

__all__ = [
    'generate_random_code',
    'generate_unique_code',
    'generate_transaction_id',
    'generate_rental_code',
    'paginate_queryset',
    'validate_phone_number',
    'mask_sensitive_data',
    'calculate_distance',
    'format_currency',
    'calculate_points_from_amount',
    'convert_points_to_amount',
    'create_success_response',
    'create_error_response',
    'get_client_ip',
    'get_late_fee_configuration',
    'calculate_late_fee_amount',
    'calculate_overdue_minutes',
    'get_package_rate_per_minute',
]
