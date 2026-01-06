from __future__ import annotations


def validate_phone_number(phone: str) -> bool:
    """Basic phone number validation for Nepal"""
    clean_phone = ''.join(filter(str.isdigit, phone))

    if len(clean_phone) == 10 and (clean_phone.startswith('98') or clean_phone.startswith('97')):
        return True

    if len(clean_phone) == 13 and (clean_phone.startswith('97798') or clean_phone.startswith('97797')):
        return True

    return False


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data like phone numbers, emails"""
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)
