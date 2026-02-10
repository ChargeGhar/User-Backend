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
from api.user.system.serializers import (
    PartnerRequestCreateSerializer,
    PartnerRequestDetailSerializer
)

partner_request_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@partner_request_router.register(r"app/partner/request", name="partner-request")
@extend_schema(
    tags=["Partners"],
    summary="Submit Partner Request",
    description="Submit partnership request (stored in Partner with PENDING status)",
    request=PartnerRequestCreateSerializer,
    responses={201: BaseResponseSerializer}
)
class PartnerRequestCreateView(GenericAPIView, BaseAPIView):
    """Submit partnership request"""
    serializer_class = PartnerRequestCreateSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Partners"],
        summary="Get Partner Request",
        description="Retrieve current user's partner request details",
        responses={200: PartnerRequestDetailSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        def operation():
            partner = PartnerRepository.get_by_user_id(request.user.id)
            if not partner:
                return None

            response = {
                'business_name': partner.business_name,
                'contact_phone': partner.contact_phone,
                'subject': partner.subject,
                'message': partner.message,
                'status': partner.status
            }

            if partner.assigned_by:
                response.update({
                    'assigned_by': {
                        'id': str(partner.assigned_by.id),
                        'username': partner.assigned_by.username,
                        'email': partner.assigned_by.email,
                        'phone_number': partner.assigned_by.phone_number
                    },
                    'assigned_at': partner.assigned_at,
                    'partner_code': partner.code,
                    'partner_type': partner.partner_type,
                    'vendor_type': partner.vendor_type,
                    'contact_email': partner.contact_email,
                    'address': partner.address,
                    'upfront_amount': float(partner.upfront_amount) if partner.upfront_amount is not None else None,
                    'revenue_share_percent': float(partner.revenue_share_percent) if partner.revenue_share_percent is not None else None,
                    'notes': partner.notes
                })

            return response

        return self.handle_service_operation(
            operation,
            success_message="Partner request retrieved successfully",
            error_message="Failed to retrieve partner request"
        )

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
