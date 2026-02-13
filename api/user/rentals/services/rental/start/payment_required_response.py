"""
Payment Required Response Builder
==================================

Handles HTTP 402 payment_required responses.
Separate from standard error_response to avoid breaking other endpoints.
"""
from rest_framework import status
from rest_framework.response import Response
from typing import Dict, Any


def build_payment_required_response(
    message: str,
    error_code: str,
    data: Dict[str, Any]
) -> Response:
    """
    Build HTTP 402 payment_required response.
    
    Args:
        message: User-friendly message
        error_code: Error code (should be 'payment_required')
        data: Payment intent and gateway details
        
    Returns:
        Response with HTTP 402 status
    """
    return Response(
        {
            'success': False,
            'message': message,
            'error_code': error_code,
            'data': data
        },
        status=status.HTTP_402_PAYMENT_REQUIRED
    )
