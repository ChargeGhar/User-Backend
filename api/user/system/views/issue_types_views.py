"""Issue types endpoint for mobile app"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.permissions import AllowAny

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.system.serializers import IssueTypesResponseSerializer
from api.user.stations.models import StationIssue
from api.user.rentals.models import RentalIssue

issue_types_router = CustomViewRouter()


@issue_types_router.register(r"app/issue-types", name="issue-types")
@extend_schema(
    tags=["App"],
    summary="Get Issue Types",
    description="Get all issue type choices for stations and rentals",
    responses={200: IssueTypesResponseSerializer}
)
class IssueTypesView(GenericAPIView, BaseAPIView):
    """Get issue type choices for dropdowns"""
    permission_classes = [AllowAny]

    @log_api_call()
    def get(self, request: Request):
        def operation():
            return {
                "station_issue_types": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in StationIssue.ISSUE_TYPE_CHOICES
                ],
                "rental_issue_types": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in RentalIssue.ISSUE_TYPE_CHOICES
                ]
            }

        return self.handle_service_operation(
            operation,
            success_message="Issue types retrieved",
            error_message="Failed to get issue types"
        )
