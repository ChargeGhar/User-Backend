"""
Admin Station Issue Management Views
"""

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.auth.permissions import IsStaffPermission
from api.common.serializers import BaseResponseSerializer
from api.admin import serializers
from api.admin.services import AdminStationService

station_issue_router = CustomViewRouter()


@station_issue_router.register(r"admin/stations/issues", name="admin-station-issues")
@extend_schema(
    tags=["Admin - Stations"],
    summary="Station Issues List",
    description="Get list of all station issues with filtering (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminStationIssuesView(GenericAPIView, BaseAPIView):
    """Admin station issues list and filtering"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all station issues with optional filtering"""
        def operation():
            # Get filter parameters
            status = request.query_params.get('status')
            priority = request.query_params.get('priority')
            station_sn = request.query_params.get('station_sn')
            issue_type = request.query_params.get('issue_type')
            ordering = request.query_params.get('ordering', '-reported_at')
            
            service = AdminStationService()
            issues = service.get_station_issues(
                status=status,
                priority=priority,
                station_sn=station_sn,
                issue_type=issue_type,
                ordering=ordering
            )
            
            serializer = serializers.AdminStationIssueSerializer(issues, many=True)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Station issues retrieved successfully",
            "Failed to retrieve station issues"
        )


@station_issue_router.register(r"admin/stations/issues/<str:issue_id>", name="admin-station-issue-detail")
@extend_schema(
    tags=["Admin - Stations"],
    summary="Station Issue Detail",
    description="Get, update or delete a specific station issue (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminStationIssueDetailView(GenericAPIView, BaseAPIView):
    """Admin station issue detail, update, and delete"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request, issue_id: str) -> Response:
        """Get specific station issue details"""
        def operation():
            service = AdminStationService()
            issue = service.get_station_issue(issue_id)
            serializer = serializers.AdminStationIssueDetailSerializer(issue)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Station issue retrieved successfully",
            "Failed to retrieve station issue"
        )
    
    @extend_schema(
        request=serializers.UpdateStationIssueSerializer
    )
    @log_api_call(include_request_data=True)
    def patch(self, request: Request, issue_id: str) -> Response:
        """Update station issue status, priority, or assignment"""
        def operation():
            serializer = serializers.UpdateStationIssueSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminStationService()
            issue = service.update_station_issue(
                issue_id=issue_id,
                admin_user=request.user,
                status=serializer.validated_data.get('status'),
                priority=serializer.validated_data.get('priority'),
                assigned_to_id=serializer.validated_data.get('assigned_to_id'),
                notes=serializer.validated_data.get('notes'),
                request=request
            )
            
            result_serializer = serializers.AdminStationIssueDetailSerializer(issue)
            return result_serializer.data
        
        return self.handle_service_operation(
            operation,
            "Station issue updated successfully",
            "Failed to update station issue"
        )
    
    @log_api_call()
    def delete(self, request: Request, issue_id: str) -> Response:
        """Delete station issue (soft delete)"""
        def operation():
            service = AdminStationService()
            return service.delete_station_issue(
                issue_id=issue_id,
                admin_user=request.user,
                request=request
            )
        
        return self.handle_service_operation(
            operation,
            "Station issue deleted successfully",
            "Failed to delete station issue"
        )
