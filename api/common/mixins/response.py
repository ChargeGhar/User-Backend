from rest_framework import status
from rest_framework.response import Response
from typing import Any, Dict, Optional

class StandardResponseMixin:
    """Mixin for standardized API responses"""
    
    def success_response(
        self, 
        data: Any = None, 
        message: str = "Success", 
        status_code: int = status.HTTP_200_OK,
        extra: Optional[Dict[str, Any]] = None
    ) -> Response:
        """Create standardized success response"""
        response_data = {
            'success': True,
            'message': message,
        }
        
        if data is not None:
            response_data['data'] = data
            
        if extra:
            response_data.update(extra)
        
        return Response(response_data, status=status_code)
    
    def error_response(
        self, 
        message: str = "Error", 
        errors: Optional[Dict[str, Any]] = None, 
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "error",
        context: Optional[Dict[str, Any]] = None
    ) -> Response:
        """Enhanced error response with context"""
        response_data = {
            'success': False,
            'error': {
                'code': error_code,
                'message': message,
            }
        }
        
        if errors:
            response_data['error']['details'] = errors
        
        if context:
            response_data['error']['context'] = context
            
        return Response(response_data, status=status_code)
