"""
Test Cases for Edge Cases and Race Conditions
=============================================
Tests concurrent operations, transaction safety, and edge cases
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db import transaction as db_transaction
from unittest.mock import patch

from api.user.advertisements.services import AdRequestService, AdPaymentService
from api.admin.services.admin_ad_service import AdminAdService
from api.user.advertisements.models import AdRequest, AdContent, AdDistribution
from api.user.payments.models import Transaction, WalletTransaction
from api.common.services.base import ServiceException


class TestTransactionSafety:
    """Test transaction atomicity and rollback"""
    
    def test_payment_rollback_on_error(self, user_with_wallet, approved_ad_request):
        """Test that payment rolls back completely on error"""
        service = AdPaymentService()
        
        initial_balance = user_with_wallet.wallet.balance
        initial_txn_count = Transaction.objects.count()
        initial_wallet_txn_count = WalletTransaction.objects.count()
        
        # Mock an error during transaction creation
        with patch.object(Transaction.objects, 'create', side_effect=Exception("Simulated error")):
            with pytest.raises(Exception):
                service.process_ad_payment(
                    ad_request_id=str(approved_ad_request.id),
                    user=user_with_wallet
                )
        
        # Verify complete rollback
        user_with_wallet.wallet.refresh_from_db()
        assert user_with_wallet.wallet.balance == initial_balance
        assert Transaction.objects.count() == initial_txn_count
        assert WalletTransaction.objects.count() == initial_wallet_txn_count
        
        approved_ad_request.refresh_from_db()
        assert approved_ad_request.status == 'PENDING_PAYMENT'
        assert approved_ad_request.paid_at is None
    
    def test_review_rollback_on_error(self, admin_user, submitted_ad_request, test_stations):
        """Test that review rolls back completely on error"""
        service = AdminAdService()
        
        original_status = submitted_ad_request.status
        station_ids = [str(s.id) for s in test_stations[:2]]
        
        # Mock an error during distribution creation
        with patch.object(AdDistribution.objects, 'create', side_effect=Exception("Simulated error")):
            with pytest.raises(Exception):
                service.review_ad_request(
                    ad_id=str(submitted_ad_request.id),
                    admin_user=admin_user,
                    validated_data={
                        'title': 'Test',
                        'description': 'Test',
                        'duration_days': 30,
                        'admin_price': Decimal('5000.00'),
                        'station_ids': station_ids,
                        'duration_seconds': 5,
                        'display_order': 0
                    }
                )
        
        # Verify rollback
        submitted_ad_request.refresh_from_db()
        assert submitted_ad_request.status == original_status
        assert submitted_ad_request.title is None or submitted_ad_request.title == ''
        assert submitted_ad_request.reviewed_by is None
    
    def test_action_rollback_on_error(self, admin_user, reviewed_ad_request):
        """Test that actions roll back on error"""
        service = AdminAdService()
        
        original_status = reviewed_ad_request.status
        
        # Mock an error during save
        with patch.object(AdRequest, 'save', side_effect=Exception("Simulated error")):
            with pytest.raises(Exception):
                service.perform_ad_action(
                    ad_id=str(reviewed_ad_request.id),
                    admin_user=admin_user,
                    action='approve',
                    data={}
                )
        
        # Verify rollback
        reviewed_ad_request.refresh_from_db()
        assert reviewed_ad_request.status == original_status
        assert reviewed_ad_request.approved_by is None


class TestConcurrentPayments:
    """Test concurrent payment scenarios"""
    
    def test_concurrent_payment_attempts(self, user_with_wallet, approved_ad_request):
        """Test that only one payment can succeed for same ad"""
        service = AdPaymentService()
        
        # First payment should succeed
        paid_ad = service.process_ad_payment(
            ad_request_id=str(approved_ad_request.id),
            user=user_with_wallet
        )
        
        assert paid_ad.status == 'PAID'
        
        # Second payment attempt should fail
        with pytest.raises(ServiceException) as exc_info:
            service.process_ad_payment(
                ad_request_id=str(paid_ad.id),
                user=user_with_wallet
            )
        
        assert exc_info.value.default_code == 'invalid_ad_status'
    
    def test_payment_with_concurrent_wallet_update(self, user_with_wallet, approved_ad_request):
        """Test payment safety with concurrent wallet operations"""
        service = AdPaymentService()
        
        initial_balance = user_with_wallet.wallet.balance
        
        # Process payment (uses select_for_update)
        paid_ad = service.process_ad_payment(
            ad_request_id=str(approved_ad_request.id),
            user=user_with_wallet
        )
        
        # Verify wallet locked during transaction
        user_with_wallet.wallet.refresh_from_db()
        expected_balance = initial_balance - approved_ad_request.admin_price
        assert user_with_wallet.wallet.balance == expected_balance


class TestMultipleAds:
    """Test scenarios with multiple ads"""
    
    def test_user_can_have_multiple_ads(self, user_with_wallet, image_media, video_media):
        """Test that user can create multiple ad requests"""
        service = AdRequestService()
        
        # Create first ad
        ad1 = service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Test User',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        # Create second ad
        ad2 = service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Test User',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(video_media.id)
            }
        )
        
        assert ad1.id != ad2.id
        assert ad1.user == ad2.user
        
        # Verify both appear in user's list
        ads = service.get_user_ad_requests(user=user_with_wallet)
        assert ad1 in ads
        assert ad2 in ads
    
    def test_multiple_payments_deduct_correctly(self, user_with_wallet, admin_user, image_media, test_stations):
        """Test that multiple ad payments deduct correctly"""
        # Create and approve two ads
        ad_service = AdRequestService()
        admin_service = AdminAdService()
        payment_service = AdPaymentService()
        
        initial_balance = user_with_wallet.wallet.balance
        
        # First ad
        ad1 = ad_service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Test',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        reviewed1 = admin_service.review_ad_request(
            ad_id=str(ad1.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Ad 1',
                'description': 'Test',
                'duration_days': 30,
                'admin_price': Decimal('2000.00'),
                'station_ids': [str(test_stations[0].id)],
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        approved1 = admin_service.perform_ad_action(
            ad_id=str(reviewed1.id),
            admin_user=admin_user,
            action='approve',
            data={}
        )
        
        paid1 = payment_service.process_ad_payment(
            ad_request_id=str(approved1.id),
            user=user_with_wallet
        )
        
        # Check balance after first payment
        user_with_wallet.wallet.refresh_from_db()
        balance_after_first = user_with_wallet.wallet.balance
        assert balance_after_first == initial_balance - Decimal('2000.00')
        
        # Second ad
        ad2 = ad_service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Test',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        reviewed2 = admin_service.review_ad_request(
            ad_id=str(ad2.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Ad 2',
                'description': 'Test',
                'duration_days': 30,
                'admin_price': Decimal('3000.00'),
                'station_ids': [str(test_stations[0].id)],
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        approved2 = admin_service.perform_ad_action(
            ad_id=str(reviewed2.id),
            admin_user=admin_user,
            action='approve',
            data={}
        )
        
        paid2 = payment_service.process_ad_payment(
            ad_request_id=str(approved2.id),
            user=user_with_wallet
        )
        
        # Check final balance
        user_with_wallet.wallet.refresh_from_db()
        final_balance = user_with_wallet.wallet.balance
        assert final_balance == initial_balance - Decimal('5000.00')


class TestDataIntegrity:
    """Test data integrity and consistency"""
    
    def test_ad_content_always_created_with_request(self, user_with_wallet, image_media):
        """Test that AdContent is always created with AdRequest"""
        service = AdRequestService()
        
        ad_request = service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Test',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        # Verify content exists
        assert ad_request.ad_contents.count() == 1
        content = ad_request.ad_contents.first()
        assert content.ad_request == ad_request
        assert content.media_upload == image_media
        assert content.is_active is True
    
    def test_distributions_cleared_on_review_update(self, admin_user, reviewed_ad_request, test_stations):
        """Test that distributions are cleared and recreated on review update"""
        service = AdminAdService()
        
        # Get initial distributions
        content = reviewed_ad_request.ad_contents.first()
        initial_count = content.ad_distributions.count()
        initial_station_ids = set(d.station.id for d in content.ad_distributions.all())
        
        # Update with different stations
        new_station_ids = [str(test_stations[2].id)]  # Different station
        
        updated_ad = service.review_ad_request(
            ad_id=str(reviewed_ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Updated',
                'description': 'Updated',
                'duration_days': 30,
                'admin_price': Decimal('5000.00'),
                'station_ids': new_station_ids,
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        # Verify distributions updated
        content.refresh_from_db()
        new_distributions = content.ad_distributions.all()
        assert new_distributions.count() == 1
        assert str(new_distributions.first().station.id) == new_station_ids[0]
    
    def test_transaction_linked_to_ad(self, user_with_wallet, approved_ad_request):
        """Test that Transaction is properly linked to AdRequest"""
        service = AdPaymentService()
        
        paid_ad = service.process_ad_payment(
            ad_request_id=str(approved_ad_request.id),
            user=user_with_wallet
        )
        
        # Verify transaction link
        assert paid_ad.transaction is not None
        assert paid_ad.transaction.user == user_with_wallet
        assert paid_ad.transaction.transaction_type == 'ADVERTISEMENT'
        
        # Verify can query from transaction
        txn = Transaction.objects.get(id=paid_ad.transaction.id)
        assert txn is not None
    
    def test_wallet_transaction_audit_trail(self, user_with_wallet, approved_ad_request):
        """Test that WalletTransaction creates proper audit trail"""
        service = AdPaymentService()
        
        initial_balance = user_with_wallet.wallet.balance
        
        paid_ad = service.process_ad_payment(
            ad_request_id=str(approved_ad_request.id),
            user=user_with_wallet
        )
        
        # Verify WalletTransaction
        wallet_txn = WalletTransaction.objects.get(
            wallet=user_with_wallet.wallet,
            transaction=paid_ad.transaction
        )
        
        assert wallet_txn.transaction_type == 'DEBIT'
        assert wallet_txn.amount == approved_ad_request.admin_price
        assert wallet_txn.balance_before == initial_balance
        assert wallet_txn.balance_after == initial_balance - approved_ad_request.admin_price
        assert wallet_txn.description is not None


class TestEdgeCaseScenarios:
    """Test unusual but valid scenarios"""
    
    def test_same_media_multiple_ads(self, user_with_wallet, image_media):
        """Test that same media can be used for multiple ads"""
        service = AdRequestService()
        
        ad1 = service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Test',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        ad2 = service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Test',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        assert ad1.ad_contents.first().media_upload == image_media
        assert ad2.ad_contents.first().media_upload == image_media
        assert ad1.id != ad2.id
    
    def test_ad_with_all_stations(self, admin_user, submitted_ad_request, test_stations):
        """Test ad distributed to all available stations"""
        service = AdminAdService()
        
        all_station_ids = [str(s.id) for s in test_stations]
        
        reviewed_ad = service.review_ad_request(
            ad_id=str(submitted_ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'All Stations',
                'description': 'Test',
                'duration_days': 30,
                'admin_price': Decimal('10000.00'),
                'station_ids': all_station_ids,
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        content = reviewed_ad.ad_contents.first()
        assert content.ad_distributions.count() == len(test_stations)
    
    def test_zero_duration_days_with_explicit_dates(self, admin_user, submitted_ad_request, test_stations):
        """Test ad with explicit start and end dates"""
        service = AdminAdService()
        
        start = date.today() + timedelta(days=1)
        end = date.today() + timedelta(days=15)
        
        reviewed_ad = service.review_ad_request(
            ad_id=str(submitted_ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Explicit Dates',
                'description': 'Test',
                'duration_days': 14,  # Should match end - start
                'admin_price': Decimal('5000.00'),
                'station_ids': [str(test_stations[0].id)],
                'start_date': start,
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        assert reviewed_ad.start_date == start
        # end_date calculated from duration_days
        assert reviewed_ad.end_date == start + timedelta(days=14)
    
    def test_very_long_duration(self, admin_user, submitted_ad_request, test_stations):
        """Test ad with very long duration"""
        service = AdminAdService()
        
        reviewed_ad = service.review_ad_request(
            ad_id=str(submitted_ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Long Duration',
                'description': 'Test',
                'duration_days': 365,  # 1 year
                'admin_price': Decimal('50000.00'),
                'station_ids': [str(test_stations[0].id)],
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        assert reviewed_ad.duration_days == 365
    
    def test_minimum_price(self, admin_user, submitted_ad_request, test_stations):
        """Test ad with minimum price"""
        service = AdminAdService()
        
        reviewed_ad = service.review_ad_request(
            ad_id=str(submitted_ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Min Price',
                'description': 'Test',
                'duration_days': 1,
                'admin_price': Decimal('0.01'),  # Minimum
                'station_ids': [str(test_stations[0].id)],
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        assert reviewed_ad.admin_price == Decimal('0.01')
