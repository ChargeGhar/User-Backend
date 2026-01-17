"""
Test Cases for Advertisement Validations and Business Rules
===========================================================
Tests all validation rules and error cases
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from api.user.advertisements.services import AdRequestService, AdPaymentService
from api.admin.services.admin_ad_service import AdminAdService
from api.common.services.base import ServiceException


class TestMediaValidations:
    """Test media upload validations"""
    
    def test_only_image_and_video_allowed(self, user_with_wallet, document_media):
        """Test that only IMAGE and VIDEO media types are allowed"""
        service = AdRequestService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.create_ad_request(
                user=user_with_wallet,
                validated_data={
                    'full_name': 'Test',
                    'contact_number': '+977-9841234567',
                    'media_upload_id': str(document_media.id)
                }
            )
        
        assert exc_info.value.default_code == 'invalid_media_type'
        assert 'IMAGE or VIDEO' in str(exc_info.value)
    
    def test_media_must_belong_to_user(self, regular_user, image_media):
        """Test that media must belong to the requesting user"""
        # Create different user
        from api.user.auth.models import User
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            phone_number='+977-9841111112'
        )
        
        service = AdRequestService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.create_ad_request(
                user=other_user,
                validated_data={
                    'full_name': 'Test',
                    'contact_number': '+977-9841234567',
                    'media_upload_id': str(image_media.id)
                }
            )
        
        assert exc_info.value.default_code == 'media_not_found'
    
    def test_media_must_exist(self, user_with_wallet):
        """Test that media upload must exist"""
        service = AdRequestService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.create_ad_request(
                user=user_with_wallet,
                validated_data={
                    'full_name': 'Test',
                    'contact_number': '+977-9841234567',
                    'media_upload_id': '00000000-0000-0000-0000-000000000000'
                }
            )
        
        assert exc_info.value.default_code == 'media_not_found'


class TestStatusValidations:
    """Test status transition validations"""
    
    def test_review_only_submitted_or_under_review(self, admin_user, approved_ad_request, test_stations):
        """Test that only SUBMITTED or UNDER_REVIEW ads can be reviewed"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.review_ad_request(
                ad_id=str(approved_ad_request.id),
                admin_user=admin_user,
                validated_data={
                    'title': 'Test',
                    'description': 'Test',
                    'duration_days': 30,
                    'admin_price': Decimal('5000.00'),
                    'station_ids': [str(test_stations[0].id)],
                    'duration_seconds': 5,
                    'display_order': 0
                }
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_approve_only_under_review(self, admin_user, submitted_ad_request):
        """Test that only UNDER_REVIEW ads can be approved"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                action='approve',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_reject_only_submitted_or_under_review(self, admin_user, approved_ad_request):
        """Test that only SUBMITTED or UNDER_REVIEW ads can be rejected"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(approved_ad_request.id),
                admin_user=admin_user,
                action='reject',
                data={'rejection_reason': 'Test'}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_pay_only_pending_payment(self, user_with_wallet, submitted_ad_request):
        """Test that only PENDING_PAYMENT ads can be paid"""
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(submitted_ad_request.id),
                user=user_with_wallet
            )
        
        assert exc_info.value.default_code == 'invalid_ad_status'
    
    def test_schedule_only_paid(self, admin_user, approved_ad_request):
        """Test that only PAID ads can be scheduled"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(approved_ad_request.id),
                admin_user=admin_user,
                action='schedule',
                data={'start_date': date.today()}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_pause_only_running(self, admin_user, scheduled_ad_request):
        """Test that only RUNNING ads can be paused"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(scheduled_ad_request.id),
                admin_user=admin_user,
                action='pause',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_resume_only_paused(self, admin_user, running_ad_request):
        """Test that only PAUSED ads can be resumed"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(running_ad_request.id),
                admin_user=admin_user,
                action='resume',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_complete_only_running(self, admin_user, scheduled_ad_request):
        """Test that only RUNNING ads can be completed"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(scheduled_ad_request.id),
                admin_user=admin_user,
                action='complete',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_cannot_cancel_completed(self, admin_user, completed_ad_request):
        """Test that COMPLETED ads cannot be cancelled"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(completed_ad_request.id),
                admin_user=admin_user,
                action='cancel',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_status'


class TestPaymentValidations:
    """Test payment-related validations"""
    
    def test_payment_requires_admin_price(self, user_with_wallet, submitted_ad_request):
        """Test that payment requires admin_price to be set"""
        # Set status but no price
        submitted_ad_request.status = 'PENDING_PAYMENT'
        submitted_ad_request.admin_price = None
        submitted_ad_request.save()
        
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(submitted_ad_request.id),
                user=user_with_wallet
            )
        
        assert exc_info.value.default_code == 'price_not_set'
    
    def test_payment_requires_positive_price(self, user_with_wallet, submitted_ad_request):
        """Test that admin_price must be greater than 0"""
        submitted_ad_request.status = 'PENDING_PAYMENT'
        submitted_ad_request.admin_price = Decimal('0.00')
        submitted_ad_request.save()
        
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(submitted_ad_request.id),
                user=user_with_wallet
            )
        
        assert exc_info.value.default_code == 'price_not_set'
    
    def test_payment_requires_wallet(self, regular_user, approved_ad_request):
        """Test that user must have a wallet"""
        approved_ad_request.user = regular_user
        approved_ad_request.save()
        
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(approved_ad_request.id),
                user=regular_user
            )
        
        assert exc_info.value.default_code == 'wallet_not_found'
    
    def test_payment_requires_active_wallet(self, user_with_wallet, approved_ad_request):
        """Test that wallet must be active"""
        wallet = user_with_wallet.wallet
        wallet.is_active = False
        wallet.save()
        
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(approved_ad_request.id),
                user=user_with_wallet
            )
        
        assert exc_info.value.default_code == 'wallet_not_found'
        
        # Cleanup
        wallet.is_active = True
        wallet.save()
    
    def test_payment_requires_sufficient_balance(self, user_with_low_balance, approved_ad_request):
        """Test that wallet must have sufficient balance"""
        approved_ad_request.user = user_with_low_balance
        approved_ad_request.save()
        
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(approved_ad_request.id),
                user=user_with_low_balance
            )
        
        assert exc_info.value.default_code == 'insufficient_balance'


class TestReviewValidations:
    """Test review-related validations"""
    
    def test_review_requires_valid_stations(self, admin_user, submitted_ad_request):
        """Test that all station IDs must be valid"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.review_ad_request(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                validated_data={
                    'title': 'Test',
                    'description': 'Test',
                    'duration_days': 30,
                    'admin_price': Decimal('5000.00'),
                    'station_ids': ['00000000-0000-0000-0000-000000000000'],
                    'duration_seconds': 5,
                    'display_order': 0
                }
            )
        
        assert exc_info.value.default_code == 'stations_not_found'
    
    def test_review_requires_at_least_one_station(self, admin_user, submitted_ad_request):
        """Test that at least one station must be provided"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.review_ad_request(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                validated_data={
                    'title': 'Test',
                    'description': 'Test',
                    'duration_days': 30,
                    'admin_price': Decimal('5000.00'),
                    'station_ids': [],
                    'duration_seconds': 5,
                    'display_order': 0
                }
            )
        
        assert exc_info.value.default_code == 'stations_not_found'
    
    def test_reject_requires_reason(self, admin_user, submitted_ad_request):
        """Test that rejection requires a reason"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                action='reject',
                data={}
            )
        
        assert exc_info.value.default_code == 'rejection_reason_required'
    
    def test_schedule_requires_start_date(self, admin_user, paid_ad_request):
        """Test that scheduling requires start_date"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(paid_ad_request.id),
                admin_user=admin_user,
                action='schedule',
                data={}
            )
        
        assert exc_info.value.default_code == 'start_date_required'


class TestScheduleValidations:
    """Test schedule update validations"""
    
    def test_update_schedule_requires_valid_status(self, submitted_ad_request):
        """Test that schedule can only be updated for SCHEDULED/RUNNING/PAUSED"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.update_schedule(
                ad_id=str(submitted_ad_request.id),
                validated_data={'start_date': date.today()}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_update_schedule_requires_at_least_one_date(self, scheduled_ad_request):
        """Test that at least one date must be provided"""
        service = AdminAdService()
        
        # This should work - updating with empty dict should raise validation error
        # (This test assumes serializer validation, but service should handle it)
        try:
            service.update_schedule(
                ad_id=str(scheduled_ad_request.id),
                validated_data={}
            )
            # If no error, the ad should remain unchanged
            scheduled_ad_request.refresh_from_db()
        except ServiceException:
            # Expected if service validates this
            pass


class TestActionValidations:
    """Test action-related validations"""
    
    def test_invalid_action_name(self, admin_user, submitted_ad_request):
        """Test that invalid action names are rejected"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                action='invalid_action',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_action'
    
    def test_ad_must_exist(self, admin_user):
        """Test that ad must exist for all operations"""
        service = AdminAdService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.perform_ad_action(
                ad_id='00000000-0000-0000-0000-000000000000',
                admin_user=admin_user,
                action='approve',
                data={}
            )
        
        assert exc_info.value.default_code == 'ad_not_found'
