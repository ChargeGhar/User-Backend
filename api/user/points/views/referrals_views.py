"""
Referral system - codes, validation, claims, and user referrals
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.points import serializers
from api.user.points.services.referral_service import ReferralService
from api.user.auth.models import User

referrals_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@referrals_router.register(r"referrals/my-code", name="referrals-my-code")
class UserReferralCodeView(GenericAPIView, BaseAPIView):
    """User referral code endpoint"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Points"],
        summary="Get user referral code",
        description="Retrieve the authenticated user's referral code",
        responses={200: serializers.UserReferralCodeResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user's referral code - REAL-TIME DATA (no caching)"""
        def operation():
            return {
                'referral_code': request.user.referral_code,
                'user_id': str(request.user.id),
                'username': request.user.username
            }

        return self.handle_service_operation(
            operation,
            "Referral code retrieved successfully",
            "Failed to retrieve referral code"
        )

@referrals_router.register(r"referrals/claim", name="referrals-claim")
class ReferralClaimView(GenericAPIView, BaseAPIView):
    """Referral claim endpoint with built-in validation"""
    serializer_class = serializers.ReferralClaimSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Points"],
        summary="Claim referral rewards",
        description="Validate and claim referral rewards after completing first rental. Includes validation logic.",
        request=serializers.ReferralClaimSerializer,
        responses={200: serializers.ReferralClaimResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Claim referral rewards with validation"""
        def operation():
            serializer = self.get_serializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)

            service = ReferralService()
            
            # Get referral code from serializer
            referral_code = serializer.validated_data['referral_code']
            
            # Validate the referral code first
            validation_result = service.validate_referral_code(referral_code, request.user)
            
            if not validation_result['valid']:
                from api.common.services.base import ServiceException
                raise ServiceException(
                    detail="Invalid referral code",
                    code="invalid_referral_code",
                    user_message=validation_result['message']
                )
            
            # Try to find existing referral record
            from api.user.points.models import Referral
            referral = Referral.objects.filter(
                referral_code=referral_code,
                invitee=request.user
            ).first()
            
            if referral:
                # Check if already completed
                if referral.status == 'COMPLETED':
                    from api.common.services.base import ServiceException
                    raise ServiceException(
                        detail="Referral already completed",
                        code="referral_already_claimed",
                        user_message="Referral rewards already claimed for this code"
                    )
                elif referral.status == 'PENDING':
                    # Use existing pending referral
                    referral_id = str(referral.id)
                else:
                    from api.common.services.base import ServiceException
                    raise ServiceException(
                        detail="Referral not eligible",
                        code="referral_not_eligible",
                        user_message="Referral is not eligible for claiming"
                    )
            else:
                # Create new referral record for claiming
                referrer = User.objects.get(id=validation_result['inviter_id'])
                
                # Set referred_by relationship
                request.user.referred_by = referrer
                request.user.save(update_fields=['referred_by'])
                
                # Create referral record
                referral = service.create_referral(referrer, request.user, referral_code)
                referral_id = str(referral.id)

            # Complete the referral (award points)
            completion_result = service.complete_referral(str(referral_id))

            return {
                'points_awarded': completion_result['invitee_points'],
                'referral_id': completion_result['referral_id'],
                'completed_at': completion_result['completed_at'],
                'validation_passed': True
            }

        return self.handle_service_operation(
            operation,
            "Referral rewards claimed successfully",
            "Failed to claim referral rewards"
        )



@referrals_router.register(r"referrals/my-referrals", name="my-referrals")
class UserReferralsView(GenericAPIView, BaseAPIView):
    """User referrals endpoint"""
    serializer_class = serializers.ReferralListSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Points"],
        summary="Get user referrals",
        description="Retrieve referrals sent by the authenticated user",
        parameters=[
            OpenApiParameter("page", int, description="Page number"),
            OpenApiParameter("page_size", int, description="Items per page"),
        ],
        responses={200: serializers.UserReferralsResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get referrals sent by user"""
        def operation():
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))

            service = ReferralService()
            referrals_data = service.get_user_referrals(request.user, page, page_size)

            # Serialize referrals with MVP list serializer
            referrals_serializer = serializers.ReferralListSerializer(
                referrals_data['results'], many=True
            )

            return {
                'results': referrals_serializer.data,
                'pagination': referrals_data['pagination']
            }

        return self.handle_service_operation(
            operation,
            "User referrals retrieved successfully",
            "Failed to retrieve user referrals"
        )

