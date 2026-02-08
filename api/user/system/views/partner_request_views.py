"""
Partner request views for mobile app.
"""
from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.common.services.base import ServiceException
from api.partners.common.models import Partner
from api.partners.common.repositories import PartnerRepository
from api.user.system.serializers import PartnerRequestCreateSerializer

partner_request_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@partner_request_router.register(r"app/partner/request", name="partner-request")
@extend_schema(
    tags=["App"],
    summary="Submit Partner Request",
    description="Submit partnership request (stored in Partner with PENDING status)",
    request=PartnerRequestCreateSerializer,
    responses={201: BaseResponseSerializer}
)
class PartnerRequestCreateView(GenericAPIView, BaseAPIView):
    """Submit partnership request"""
    serializer_class = PartnerRequestCreateSerializer
    permission_classes = [IsAuthenticated]

    @log_api_call()
    def post(self, request: Request) -> Response:
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            if PartnerRepository.user_is_already_partner(request.user.id):
                raise ServiceException(
                    detail="User is already a partner",
                    code="user_already_partner"
                )

            # Default request as NON_REVENUE vendor (pending)
            partner = PartnerRepository.create(
                user_id=request.user.id,
                partner_type=Partner.PartnerType.VENDOR,
                vendor_type=Partner.VendorType.NON_REVENUE,
                business_name=data['full_name'],
                contact_phone=data['contact_number'],
                assigned_by_id=None,
                subject=data['subject'],
                message=data.get('message'),
                status=Partner.Status.PENDING
            )

            return {
                'id': str(partner.id),
                'status': partner.status,
                'created_at': partner.created_at
            }

        return self.handle_service_operation(
            operation,
            success_message="Partner request submitted successfully",
            error_message="Failed to submit partner request",
            success_status=status.HTTP_201_CREATED
        )
