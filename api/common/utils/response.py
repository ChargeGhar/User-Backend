from __future__ import annotations

from typing import Any, Dict, Optional
from rest_framework.response import Response
from rest_framework import status


def create_success_response(data: Any = None, message: str = "Success", status_code: int = status.HTTP_200_OK) -> Response:
    """Create standardized success response"""
    response_data = {
        'success': True,
        'message': message,
    }
    if data is not None:
        response_data['data'] = data
    
    return Response(response_data, status=status_code)


def create_error_response(message: str = "Error", errors: Optional[Dict[str, Any]] = None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    """Create standardized error response"""
    response_data = {
        'success': False,
        'message': message,
    }
    if errors:
        response_data['errors'] = errors
    
    return Response(response_data, status=status_code)


def get_client_ip(request) -> str:
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1'
