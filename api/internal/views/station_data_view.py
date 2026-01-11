"""
Internal API views for IoT system integration
Endpoints for receiving device data from Java IoT management system
"""
from __future__ import annotations

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.user.auth.permissions import IsStaffPermission
from django.db import transaction
from drf_spectacular.utils import extend_schema

from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.internal.services import StationSyncService
from api.common.utils.signature import get_signature_util
from api.common.services.base import ServiceException

logger = logging.getLogger(__name__)


class StationDataInternalView(APIView, BaseAPIView):
    """
    Internal endpoint for receiving station data from IoT system
    
    POST /api/internal/stations/data
    
    Handles three types of data:
    - type=full: Complete station synchronization (device upload)
    - type=returned: PowerBank return event notification
    - type=status: Device status change (online/offline)
    """
    
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        operation_id="internal_station_data_sync",
        tags=["Internal - IoT Integration"],
        summary="Sync Station Data from IoT System",
        description="Internal endpoint for receiving station data from Java IoT management system.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'type': {'type': 'string', 'enum': ['full', 'returned', 'status']},
                    'timestamp': {'type': 'integer'},
                    'device': {'type': 'object'},
                    'station': {'type': 'object'},
                    'slots': {'type': 'array'},
                    'power_banks': {'type': 'array'}
                },
                'required': ['type', 'timestamp', 'device']
            }
        },
        responses={200: {'type': 'object'}, 400: {'type': 'object'}, 403: {'type': 'object'}}
    )
    @log_api_call()
    def post(self, request):
        """Process incoming station data from IoT system"""
        def operation():
            self._validate_request_signature(request)
            
            data = request.data
            data_type = data.get('type')
            
            logger.info(f"Received IoT data sync request: type={data_type}")
            
            if data_type == 'full':
                return self._handle_full_sync(data)
            elif data_type == 'returned':
                return self._handle_return_event(data)
            elif data_type == 'status':
                return self._handle_status(data)
            else:
                raise ServiceException(
                    detail=f'Invalid data type: {data_type}. Must be "full", "returned", or "status"',
                    code="invalid_type"
                )
        
        return self.handle_service_operation(
            operation,
            success_message="IoT data processed successfully",
            error_message="Failed to process IoT data"
        )
    
    def _validate_request_signature(self, request):
        """Validate HMAC signature from IoT system"""
        signature = request.META.get('HTTP_X_SIGNATURE')
        timestamp_str = request.META.get('HTTP_X_TIMESTAMP')
        
        if not signature or not timestamp_str:
            raise ServiceException(
                detail='Missing signature or timestamp headers (X-Signature, X-Timestamp)',
                code="missing_headers"
            )
        
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise ServiceException(detail='Invalid timestamp format', code="invalid_timestamp")
        
        try:
            if request.content_type == 'application/json':
                payload = request.body.decode('utf-8')
            else:
                raise ServiceException(detail='Content-Type must be application/json', code="invalid_content_type")
        except Exception as e:
            raise ServiceException(detail=f'Error reading request body: {str(e)}', code="body_read_error")
        
        signature_util = get_signature_util()
        is_valid, error_message = signature_util.validate_signature(
            payload=payload, timestamp=timestamp, received_signature=signature
        )
        
        if not is_valid:
            raise ServiceException(detail=f'Signature validation failed: {error_message}', code="invalid_signature")

    def _handle_full_sync(self, data):
        """Handle full station synchronization"""
        try:
            service = StationSyncService()
            with transaction.atomic():
                result = service.sync_station_data(data)
            logger.info(f"Station sync successful: {result}")
            return result
        except ServiceException:
            raise
        except Exception as e:
            logger.error(f"Error in full sync: {str(e)}", exc_info=True)
            raise ServiceException(detail=f'Sync failed: {str(e)}', code="sync_error")
    
    def _handle_return_event(self, data):
        """Handle PowerBank return event notification"""
        try:
            service = StationSyncService()
            with transaction.atomic():
                result = service.process_return_event(data)
            logger.info(f"Return event processed: {result}")
            return result
        except ServiceException:
            raise
        except Exception as e:
            logger.error(f"Error processing return: {str(e)}", exc_info=True)
            raise ServiceException(detail=f'Return processing failed: {str(e)}', code="return_error")
    
    def _handle_status(self, data):
        """Handle device status change (online/offline/maintenance)"""
        try:
            service = StationSyncService()
            with transaction.atomic():
                result = service.update_station_status(data)
            logger.info(f"Status update processed: {result}")
            return result
        except ServiceException:
            raise
        except Exception as e:
            logger.error(f"Error processing status update: {str(e)}", exc_info=True)
            raise ServiceException(detail=f'Status update failed: {str(e)}', code="status_update_error")
