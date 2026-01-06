from __future__ import annotations

import random
import string
from django.utils import timezone


def generate_random_code(length: int = 6, include_letters: bool = True, include_numbers: bool = True) -> str:
    """Generate random alphanumeric code"""
    chars = ""
    if include_letters:
        chars += string.ascii_uppercase
    if include_numbers:
        chars += string.digits
    
    if not chars:
        raise ValueError("At least one character type must be included")
    
    return ''.join(random.choices(chars, k=length))


def generate_unique_code(prefix: str = "", length: int = 8) -> str:
    """Generate unique code with optional prefix"""
    code = generate_random_code(length)
    return f"{prefix}{code}" if prefix else code


def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    random_part = generate_random_code(6)
    return f"TXN{timestamp}{random_part}"


def generate_rental_code() -> str:
    """Generate unique rental code"""
    return generate_random_code(8, include_letters=True, include_numbers=True)
