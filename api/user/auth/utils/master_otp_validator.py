"""Master OTP validator for development/testing"""
from api.user.system.services import AppConfigService


def is_master_otp_enabled() -> bool:
    """Check if master OTP is enabled"""
    config_service = AppConfigService()
    return config_service.get_config_cached('MASTER_OTP_ENABLED', 'false').lower() == 'true'


def get_master_otp_numbers() -> list:
    """Get list of master OTP numbers"""
    config_service = AppConfigService()
    numbers_str = config_service.get_config_cached('MASTER_OTP_NUMBERS', '')
    return [n.strip() for n in numbers_str.split(',') if n.strip()]


def get_master_otp() -> str:
    """Get master OTP value"""
    config_service = AppConfigService()
    return config_service.get_config_cached('MASTER_OTP', '')


def is_master_number(identifier: str) -> bool:
    """Check if identifier is in master OTP numbers list"""
    if not is_master_otp_enabled():
        return False
    
    master_numbers = get_master_otp_numbers()
    if identifier in master_numbers:
        return True
    
    # Check for partial matches or normalized matches (e.g. without +977)
    normalized_identifier = identifier.replace('+', '')
    if normalized_identifier.startswith('977'):
        normalized_identifier = normalized_identifier[3:]
        
    for num in master_numbers:
        normalized_num = num.replace('+', '')
        if normalized_num.startswith('977'):
            normalized_num = normalized_num[3:]
        if normalized_identifier == normalized_num:
            return True
            
    return False


def validate_master_otp(identifier: str, otp: str) -> bool:
    """Validate master OTP - requires BOTH identifier in list AND OTP match"""
    if not is_master_otp_enabled():
        return False
    return is_master_number(identifier) and otp == get_master_otp()
