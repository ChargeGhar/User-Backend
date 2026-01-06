import logging
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class ServiceHandlerMixin:
    """Mixin for handling service layer operations"""
    
    def handle_service_operation(
        self, 
        operation_func,
        success_message: str = "Operation successful",
        error_message: str = "Operation failed",
        success_status: int = status.HTTP_200_OK,
        operation_context: str = None
    ) -> Response:
        """Enhanced service operation handler with context"""
        try:
            result = operation_func()
            
            if hasattr(self, 'success_response'):
                return self.success_response(
                    data=result,
                    message=success_message,
                    status_code=success_status
                )
            else:
                return Response(result, status=success_status)
                
        except Exception as e:
            logger.error(f"Service operation failed: {str(e)}")
            
            from api.common.services.base import ServiceException
            from rest_framework.exceptions import ValidationError
            
            if isinstance(e, ValidationError):
                error_code = 'validation_error'
                status_code = status.HTTP_400_BAD_REQUEST
                user_message = str(e)
                error_context = {'validation_errors': e.detail} if hasattr(e, 'detail') else None
            elif isinstance(e, ServiceException):
                error_code = getattr(e, 'default_code', 'service_error')
                user_message = str(e)
                error_context = None
                status_code = getattr(e, 'status_code', status.HTTP_400_BAD_REQUEST)
            else:
                error_code = 'internal_error'
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                user_message = error_message
                error_context = None
            
            if hasattr(self, 'error_response'):
                return self.error_response(
                    message=user_message,
                    status_code=status_code,
                    error_code=error_code,
                    context={'operation': operation_context} if operation_context else error_context
                )
            else:
                return Response({'error': user_message}, status=status_code)
