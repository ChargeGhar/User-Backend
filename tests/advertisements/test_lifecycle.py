"""
Test Cases for Complete Advertisement Lifecycle
===============================================
Tests the full flow from submission to completion
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from api.user.advertisements.services import AdRequestService, AdPaymentService
from api.admin.services.admin_ad_service import AdminAdService
from api.user.advertisements.models import AdRequest
from api.user.payments.models import Transaction, WalletTransaction


class TestCompleteLifecycle:
    """Test complete advertisement lifecycle"""
    
    def test_full_lifecycle_success(self, user_with_wallet, admin_user, image_media, test_stations):
        """Test complete flow: Submit → Review → Approve → Pay → Schedule → Run → Complete"""
        
        # STEP 1: User submits ad request
        ad_service = AdRequestService()
        ad_request = ad_service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Lifecycle Test Advertiser',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        assert ad_request.status == 'SUBMITTED'
        assert ad_request.submitted_at is not None
        print(f"✅ Step 1: Ad submitted - {ad_request.id}")
        
        # STEP 2: Admin reviews and sets pricing
        admin_service = AdminAdService()
        station_ids = [str(s.id) for s in test_stations[:2]]
        
        reviewed_ad = admin_service.review_ad_request(
            ad_id=str(ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Lifecycle Test Campaign',
                'description': 'Testing complete lifecycle',
                'duration_days': 30,
                'admin_price': Decimal('5000.00'),
                'admin_notes': 'Approved for testing',
                'station_ids': station_ids,
                'duration_seconds': 7,
                'display_order': 0
            }
        )
        
        assert reviewed_ad.status == 'UNDER_REVIEW'
        assert reviewed_ad.admin_price == Decimal('5000.00')
        assert reviewed_ad.ad_contents.first().ad_distributions.count() == 2
        print(f"✅ Step 2: Ad reviewed - Price: NPR {reviewed_ad.admin_price}")
        
        # STEP 3: Admin approves
        approved_ad = admin_service.perform_ad_action(
            ad_id=str(reviewed_ad.id),
            admin_user=admin_user,
            action='approve',
            data={}
        )
        
        assert approved_ad.status == 'PENDING_PAYMENT'
        assert approved_ad.approved_by == admin_user
        print(f"✅ Step 3: Ad approved - Status: {approved_ad.status}")
        
        # STEP 4: User pays
        payment_service = AdPaymentService()
        initial_balance = user_with_wallet.wallet.balance
        
        paid_ad = payment_service.process_ad_payment(
            ad_request_id=str(approved_ad.id),
            user=user_with_wallet
        )
        
        assert paid_ad.status == 'PAID'
        assert paid_ad.transaction is not None
        assert paid_ad.transaction.status == 'SUCCESS'
        
        user_with_wallet.wallet.refresh_from_db()
        assert user_with_wallet.wallet.balance == initial_balance - Decimal('5000.00')
        print(f"✅ Step 4: Payment processed - Transaction: {paid_ad.transaction.transaction_id}")
        
        # STEP 5: Admin schedules
        start_date = date.today() + timedelta(days=1)
        
        scheduled_ad = admin_service.perform_ad_action(
            ad_id=str(paid_ad.id),
            admin_user=admin_user,
            action='schedule',
            data={'start_date': start_date}
        )
        
        assert scheduled_ad.status == 'SCHEDULED'
        assert scheduled_ad.start_date == start_date
        assert scheduled_ad.end_date == start_date + timedelta(days=30)
        print(f"✅ Step 5: Ad scheduled - Start: {scheduled_ad.start_date}")
        
        # STEP 6: Simulate ad running (would be done by cron)
        scheduled_ad.status = 'RUNNING'
        scheduled_ad.start_date = date.today()
        scheduled_ad.save()
        
        assert scheduled_ad.status == 'RUNNING'
        print(f"✅ Step 6: Ad running")
        
        # STEP 7: Admin completes ad
        completed_ad = admin_service.perform_ad_action(
            ad_id=str(scheduled_ad.id),
            admin_user=admin_user,
            action='complete',
            data={}
        )
        
        assert completed_ad.status == 'COMPLETED'
        assert completed_ad.completed_at is not None
        print(f"✅ Step 7: Ad completed - Completed at: {completed_ad.completed_at}")
        
        # Verify final state
        final_ad = AdRequest.objects.get(id=ad_request.id)
        assert final_ad.status == 'COMPLETED'
        assert final_ad.submitted_at is not None
        assert final_ad.reviewed_at is not None
        assert final_ad.approved_at is not None
        assert final_ad.paid_at is not None
        assert final_ad.completed_at is not None
        
        print(f"✅ LIFECYCLE COMPLETE: {ad_request.rental_code if hasattr(ad_request, 'rental_code') else ad_request.id}")
    
    def test_lifecycle_with_rejection(self, user_with_wallet, admin_user, image_media):
        """Test lifecycle with rejection"""
        
        # Submit
        ad_service = AdRequestService()
        ad_request = ad_service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Rejection Test',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        assert ad_request.status == 'SUBMITTED'
        
        # Reject
        admin_service = AdminAdService()
        rejected_ad = admin_service.perform_ad_action(
            ad_id=str(ad_request.id),
            admin_user=admin_user,
            action='reject',
            data={'rejection_reason': 'Content violates policy'}
        )
        
        assert rejected_ad.status == 'REJECTED'
        assert rejected_ad.rejection_reason == 'Content violates policy'
        assert rejected_ad.reviewed_by == admin_user
        
        # Verify cannot proceed further
        from api.common.services.base import ServiceException
        with pytest.raises(ServiceException):
            admin_service.perform_ad_action(
                ad_id=str(rejected_ad.id),
                admin_user=admin_user,
                action='approve',
                data={}
            )
    
    def test_lifecycle_with_cancellation(self, user_with_wallet, admin_user, image_media, test_stations):
        """Test lifecycle with cancellation after payment"""
        
        # Submit → Review → Approve → Pay
        ad_service = AdRequestService()
        ad_request = ad_service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Cancel Test',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        admin_service = AdminAdService()
        reviewed_ad = admin_service.review_ad_request(
            ad_id=str(ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Cancel Test',
                'description': 'Test',
                'duration_days': 30,
                'admin_price': Decimal('3000.00'),
                'station_ids': [str(test_stations[0].id)],
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        approved_ad = admin_service.perform_ad_action(
            ad_id=str(reviewed_ad.id),
            admin_user=admin_user,
            action='approve',
            data={}
        )
        
        payment_service = AdPaymentService()
        paid_ad = payment_service.process_ad_payment(
            ad_request_id=str(approved_ad.id),
            user=user_with_wallet
        )
        
        assert paid_ad.status == 'PAID'
        
        # Cancel
        cancelled_ad = admin_service.perform_ad_action(
            ad_id=str(paid_ad.id),
            admin_user=admin_user,
            action='cancel',
            data={'reason': 'User requested cancellation'}
        )
        
        assert cancelled_ad.status == 'CANCELLED'
        assert 'User requested cancellation' in cancelled_ad.admin_notes
        
        # Payment should still exist (no refund in current implementation)
        assert cancelled_ad.transaction is not None
        assert cancelled_ad.paid_at is not None
    
    def test_lifecycle_with_pause_resume(self, user_with_wallet, admin_user, image_media, test_stations):
        """Test lifecycle with pause and resume"""
        
        # Submit → Review → Approve → Pay → Schedule → Run
        ad_service = AdRequestService()
        ad_request = ad_service.create_ad_request(
            user=user_with_wallet,
            validated_data={
                'full_name': 'Pause Test',
                'contact_number': '+977-9841234567',
                'media_upload_id': str(image_media.id)
            }
        )
        
        admin_service = AdminAdService()
        reviewed_ad = admin_service.review_ad_request(
            ad_id=str(ad_request.id),
            admin_user=admin_user,
            validated_data={
                'title': 'Pause Test',
                'description': 'Test',
                'duration_days': 30,
                'admin_price': Decimal('4000.00'),
                'station_ids': [str(test_stations[0].id)],
                'duration_seconds': 5,
                'display_order': 0
            }
        )
        
        approved_ad = admin_service.perform_ad_action(
            ad_id=str(reviewed_ad.id),
            admin_user=admin_user,
            action='approve',
            data={}
        )
        
        payment_service = AdPaymentService()
        paid_ad = payment_service.process_ad_payment(
            ad_request_id=str(approved_ad.id),
            user=user_with_wallet
        )
        
        scheduled_ad = admin_service.perform_ad_action(
            ad_id=str(paid_ad.id),
            admin_user=admin_user,
            action='schedule',
            data={'start_date': date.today()}
        )
        
        # Simulate running
        scheduled_ad.status = 'RUNNING'
        scheduled_ad.save()
        
        # Pause
        paused_ad = admin_service.perform_ad_action(
            ad_id=str(scheduled_ad.id),
            admin_user=admin_user,
            action='pause',
            data={}
        )
        
        assert paused_ad.status == 'PAUSED'
        
        # Resume
        resumed_ad = admin_service.perform_ad_action(
            ad_id=str(paused_ad.id),
            admin_user=admin_user,
            action='resume',
            data={}
        )
        
        assert resumed_ad.status == 'RUNNING'
        
        # Complete
        completed_ad = admin_service.perform_ad_action(
            ad_id=str(resumed_ad.id),
            admin_user=admin_user,
            action='complete',
            data={}
        )
        
        assert completed_ad.status == 'COMPLETED'


class TestLifecycleEdgeCases:
    """Test edge cases in lifecycle"""
    
    def test_cannot_pay_twice(self, user_with_wallet, paid_ad_request):
        """Test that payment cannot be processed twice"""
        payment_service = AdPaymentService()
        
        from api.common.services.base import ServiceException
        with pytest.raises(ServiceException) as exc_info:
            payment_service.process_ad_payment(
                ad_request_id=str(paid_ad_request.id),
                user=user_with_wallet
            )
        
        assert exc_info.value.default_code == 'invalid_ad_status'
    
    def test_cannot_approve_without_review(self, admin_user, submitted_ad_request):
        """Test that ad cannot be approved without review"""
        admin_service = AdminAdService()
        
        from api.common.services.base import ServiceException
        with pytest.raises(ServiceException) as exc_info:
            admin_service.perform_ad_action(
                ad_id=str(submitted_ad_request.id),
                admin_user=admin_user,
                action='approve',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_cannot_schedule_without_payment(self, admin_user, approved_ad_request):
        """Test that ad cannot be scheduled without payment"""
        admin_service = AdminAdService()
        
        from api.common.services.base import ServiceException
        with pytest.raises(ServiceException) as exc_info:
            admin_service.perform_ad_action(
                ad_id=str(approved_ad_request.id),
                admin_user=admin_user,
                action='schedule',
                data={'start_date': date.today()}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_cannot_complete_non_running_ad(self, admin_user, scheduled_ad_request):
        """Test that only running ads can be completed"""
        admin_service = AdminAdService()
        
        from api.common.services.base import ServiceException
        with pytest.raises(ServiceException) as exc_info:
            admin_service.perform_ad_action(
                ad_id=str(scheduled_ad_request.id),
                admin_user=admin_user,
                action='complete',
                data={}
            )
        
        assert exc_info.value.default_code == 'invalid_status'
    
    def test_transaction_audit_trail(self, user_with_wallet, approved_ad_request):
        """Test that payment creates proper audit trail"""
        payment_service = AdPaymentService()
        
        initial_balance = user_with_wallet.wallet.balance
        
        paid_ad = payment_service.process_ad_payment(
            ad_request_id=str(approved_ad_request.id),
            user=user_with_wallet
        )
        
        # Verify Transaction
        txn = paid_ad.transaction
        assert txn.user == user_with_wallet
        assert txn.transaction_type == 'ADVERTISEMENT'
        assert txn.amount == approved_ad_request.admin_price
        assert txn.status == 'SUCCESS'
        
        # Verify WalletTransaction
        wallet_txn = WalletTransaction.objects.get(
            wallet=user_with_wallet.wallet,
            transaction=txn
        )
        assert wallet_txn.transaction_type == 'DEBIT'
        assert wallet_txn.amount == approved_ad_request.admin_price
        assert wallet_txn.balance_before == initial_balance
        assert wallet_txn.balance_after == initial_balance - approved_ad_request.admin_price
