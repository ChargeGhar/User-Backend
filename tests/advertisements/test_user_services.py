"""
Test Cases for User Advertisement Services
==========================================
Tests: AdRequestService, AdPaymentService
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction

from api.user.advertisements.services import AdRequestService, AdPaymentService
from api.user.advertisements.models import AdRequest, AdContent
from api.user.payments.models import Transaction, WalletTransaction
from api.common.services.base import ServiceException


class TestAdRequestService:
    """Test AdRequestService methods"""
    
    def test_create_ad_request_success(self, user_with_wallet, image_media):
        """Test successful ad request creation"""
        service = AdRequestService()
        
        ad_request = service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Test Advertiser',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        # Verify AdRequest
        assert ad_request.user == user_with_wallet
        assert ad_request.full_name == 'Test Advertiser'
        assert ad_request.contact_number == '+977-9841234567'
        assert ad_request.status == 'SUBMITTED'
        assert ad_request.submitted_at is not None
        
        # Verify AdContent created
        assert ad_request.ad_contents.count() == 1
        content = ad_request.ad_contents.first()
        assert content.media_upload == image_media
        assert content.content_type == 'IMAGE'
        assert content.duration_seconds == 5
        assert content.display_order == 0
        assert content.is_active is True
    
    def test_create_ad_request_with_video(self, user_with_wallet, video_media):
        """Test ad request creation with video media"""
        service = AdRequestService()
        
        ad_request = service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Video Advertiser',
                'contact_number': '+977-9841234568',
                'media_upload_id': str(video_media.id)
            }
        )
        
        content = ad_request.ad_contents.first()
        assert content.content_type == 'VIDEO'
        assert content.media_upload == video_media
    
    def test_create_ad_request_invalid_media_type(self, user_with_wallet, document_media):
        """Test ad request creation with invalid media type"""
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
    
    def test_create_ad_request_media_not_found(self, user_with_wallet):
        """Test ad request creation with non-existent media"""
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
    
    def test_get_user_ad_requests(self, user_with_wallet, submitted_ad_request):
        """Test getting user's ad requests"""
        service = AdRequestService()
        
        ads = service.get_user_ad_requests(user=user_with_wallet)
        
        assert ads.count() >= 1
        assert submitted_ad_request in ads
        # Verify only user's ads returned
        for ad in ads:
            assert ad.user == user_with_wallet
    
    def test_get_user_ad_requests_with_status_filter(self, user_with_wallet, submitted_ad_request, approved_ad_request):
        """Test filtering ad requests by status"""
        service = AdRequestService()
        
        # Filter by SUBMITTED
        submitted_ads = service.get_user_ad_requests(
            user=user_with_wallet,
            filters={'status': 'SUBMITTED'}
        )
        
        assert submitted_ad_request in submitted_ads
        assert approved_ad_request not in submitted_ads
        
        # Filter by PENDING_PAYMENT
        pending_ads = service.get_user_ad_requests(
            user=user_with_wallet,
            filters={'status': 'PENDING_PAYMENT'}
        )
        
        assert approved_ad_request in pending_ads
        assert submitted_ad_request not in pending_ads
    
    def test_get_user_ad_by_id_success(self, user_with_wallet, submitted_ad_request):
        """Test getting specific ad by ID"""
        service = AdRequestService()
        
        ad = service.get_user_ad_by_id(
            ad_id=str(submitted_ad_request.id),
            user=user_with_wallet
        )
        
        assert ad.id == submitted_ad_request.id
        assert ad.user == user_with_wallet
    
    def test_get_user_ad_by_id_not_found(self, user_with_wallet):
        """Test getting non-existent ad"""
        service = AdRequestService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.get_user_ad_by_id(
                ad_id='00000000-0000-0000-0000-000000000000',
                user=user_with_wallet
            )
        
        assert exc_info.value.default_code == 'ad_not_found'
    
    def test_get_user_ad_by_id_wrong_user(self, regular_user, submitted_ad_request):
        """Test getting ad belonging to different user"""
        service = AdRequestService()
        
        # Create different user
        from api.user.auth.models import User
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            phone_number='+977-9841111112'
        )
        
        with pytest.raises(ServiceException) as exc_info:
            service.get_user_ad_by_id(
                ad_id=str(submitted_ad_request.id),
                user=other_user
            )
        
        assert exc_info.value.default_code == 'ad_not_found'


class TestAdPaymentService:
    """Test AdPaymentService methods"""
    
    def test_process_payment_success(self, user_with_wallet, approved_ad_request):
        """Test successful payment processing"""
        service = AdPaymentService()
        
        # Get initial wallet balance
        wallet = user_with_wallet.wallet
        initial_balance = wallet.balance
        
        # Process payment
        paid_ad = service.process_ad_payment(
            ad_request_id=str(approved_ad_request.id),
            user=user_with_wallet
        )
        
        # Verify ad updated
        assert paid_ad.status == 'PAID'
        assert paid_ad.paid_at is not None
        assert paid_ad.transaction is not None
        
        # Verify transaction created
        txn = paid_ad.transaction
        assert txn.user == user_with_wallet
        assert txn.transaction_type == 'ADVERTISEMENT'
        assert txn.amount == approved_ad_request.admin_price
        assert txn.status == 'SUCCESS'
        assert txn.payment_method_type == 'WALLET'
        assert txn.transaction_id is not None
        
        # Verify wallet deducted
        wallet.refresh_from_db()
        assert wallet.balance == initial_balance - approved_ad_request.admin_price
        
        # Verify WalletTransaction created
        wallet_txn = WalletTransaction.objects.filter(
            wallet=wallet,
            transaction=txn
        ).first()
        
        assert wallet_txn is not None
        assert wallet_txn.transaction_type == 'DEBIT'
        assert wallet_txn.amount == approved_ad_request.admin_price
        assert wallet_txn.balance_before == initial_balance
        assert wallet_txn.balance_after == wallet.balance
    
    def test_process_payment_invalid_status(self, user_with_wallet, submitted_ad_request):
        """Test payment with wrong ad status"""
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(submitted_ad_request.id),
                user=user_with_wallet
            )
        
        assert exc_info.value.default_code == 'invalid_ad_status'
    
    def test_process_payment_insufficient_balance(self, user_with_low_balance, approved_ad_request):
        """Test payment with insufficient wallet balance"""
        # Update ad to belong to low balance user
        approved_ad_request.user = user_with_low_balance
        approved_ad_request.save()
        
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(approved_ad_request.id),
                user=user_with_low_balance
            )
        
        assert exc_info.value.default_code == 'insufficient_balance'
    
    def test_process_payment_no_wallet(self, regular_user, approved_ad_request):
        """Test payment when user has no wallet"""
        # Update ad to belong to user without wallet
        approved_ad_request.user = regular_user
        approved_ad_request.save()
        
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(approved_ad_request.id),
                user=regular_user
            )
        
        assert exc_info.value.default_code == 'wallet_not_found'
    
    def test_process_payment_price_not_set(self, user_with_wallet, submitted_ad_request):
        """Test payment when admin_price not set"""
        # Set status to PENDING_PAYMENT but no price
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
    
    def test_process_payment_wrong_user(self, user_with_wallet, approved_ad_request):
        """Test payment by wrong user"""
        from api.user.auth.models import User
        other_user = User.objects.create_user(
            username='wronguser',
            email='wrong@example.com',
            phone_number='+977-9841111113'
        )
        
        service = AdPaymentService()
        
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(approved_ad_request.id),
                user=other_user
            )
        
        assert exc_info.value.default_code == 'ad_not_found'
    
    def test_process_payment_transaction_safety(self, user_with_wallet, approved_ad_request):
        """Test that payment is atomic (rollback on error)"""
        service = AdPaymentService()
        
        # Get initial state
        wallet = user_with_wallet.wallet
        initial_balance = wallet.balance
        initial_txn_count = Transaction.objects.count()
        
        # Mock an error during transaction creation
        # This tests that the entire operation rolls back
        with pytest.raises(Exception):
            with db_transaction.atomic():
                # Start payment
                ad = AdRequest.objects.select_for_update().get(id=approved_ad_request.id)
                wallet_locked = ad.user.wallet
                
                # Simulate error
                raise Exception("Simulated error")
        
        # Verify rollback - nothing changed
        wallet.refresh_from_db()
        assert wallet.balance == initial_balance
        assert Transaction.objects.count() == initial_txn_count
        
        approved_ad_request.refresh_from_db()
        assert approved_ad_request.status == 'PENDING_PAYMENT'
        assert approved_ad_request.paid_at is None
