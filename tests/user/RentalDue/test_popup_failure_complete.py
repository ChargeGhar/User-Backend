#!/usr/bin/env python3
"""
Complete popup failure test - simulates real scenario
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station
from api.user.payments.models import Transaction, WalletTransaction
from api.user.points.models import PointsTransaction, UserPoints
from api.user.payments.services.rental_payment import RentalPaymentService
from api.user.payments.services import WalletService
from api.user.points.services import award_points

User = get_user_model()

def simulate_popup_failure_refund():
    print("=== COMPLETE POPUP FAILURE REFUND TEST ===\n")
    
    # Get test data
    user = User.objects.get(id=1)
    package = RentalPackage.objects.filter(payment_model='PREPAID', price=50).first()
    station = Station.objects.filter(status='ONLINE').first()
    
    if not package or not station:
        print("❌ Missing test data")
        return False
    
    # Record initial balances
    initial_wallet = user.wallet.balance
    user_points = UserPoints.objects.get(user=user)
    initial_points = user_points.current_points
    
    print(f"Initial Balances:")
    print(f"  Wallet: NPR {initial_wallet}")
    print(f"  Points: {initial_points}")
    
    # Create test rental
    rental = Rental.objects.create(
        user=user,
        station=station,
        package=package,
        rental_code=f'TEST-POPUP-FAIL-{int(timezone.now().timestamp())}',
        status='PENDING_POPUP',
        amount_paid=Decimal('0'),
        payment_status='PENDING'
    )
    
    print(f"\nCreated rental: {rental.rental_code}")
    
    # COMBINATION payment (30 wallet + 200 points = 50 total)
    payment_breakdown = {
        'wallet_amount': Decimal('30.00'),
        'points_to_use': 200,
        'points_amount': Decimal('20.00')
    }
    
    print(f"\nPayment Breakdown:")
    print(f"  Wallet: NPR {payment_breakdown['wallet_amount']}")
    print(f"  Points: {payment_breakdown['points_to_use']} = NPR {payment_breakdown['points_amount']}")
    print(f"  Total: NPR {payment_breakdown['wallet_amount'] + payment_breakdown['points_amount']}")
    
    try:
        # STEP 1: Process payment (what happens before popup)
        print(f"\n🔄 Processing payment...")
        service = RentalPaymentService()
        txn = service.process_rental_payment(user, rental, payment_breakdown)
        
        rental.amount_paid = txn.amount
        rental.payment_status = 'PAID'
        rental.save(update_fields=['amount_paid', 'payment_status'])
        
        print(f"✅ Payment processed:")
        print(f"  Transaction: {txn.transaction_id}")
        print(f"  Method: {txn.payment_method_type}")
        print(f"  Amount: NPR {txn.amount}")
        print(f"  Gateway Response: {txn.gateway_response}")
        
        # Check balances after payment
        user.wallet.refresh_from_db()
        user_points.refresh_from_db()
        
        after_payment_wallet = user.wallet.balance
        after_payment_points = user_points.current_points
        
        wallet_deducted = initial_wallet - after_payment_wallet
        points_deducted = initial_points - after_payment_points
        
        print(f"\nBalances After Payment:")
        print(f"  Wallet: NPR {after_payment_wallet} (deducted: {wallet_deducted})")
        print(f"  Points: {after_payment_points} (deducted: {points_deducted})")
        
        # Verify deductions are correct
        wallet_correct = abs(wallet_deducted - Decimal('30.00')) < Decimal('0.01')
        points_correct = points_deducted == 200
        
        if not (wallet_correct and points_correct):
            print(f"❌ Payment deduction incorrect")
            return False
        
        print(f"✅ Payment deductions correct")
        
        # STEP 2: Simulate popup failure refund
        print(f"\n🔄 Simulating popup failure refund...")
        
        # This is the exact logic from tasks.py
        gateway_response = txn.gateway_response or {}
        gateway_wallet_amount = Decimal(str(gateway_response.get('wallet_amount', '0')))
        gateway_points_used = int(gateway_response.get('points_used', 0))
        
        # Get actual amounts from related transactions
        wallet_txn = WalletTransaction.objects.filter(
            transaction=txn, transaction_type='DEBIT'
        ).first()
        
        points_txn = PointsTransaction.objects.filter(
            related_rental=rental, transaction_type='SPENT', source='RENTAL_PAYMENT'
        ).first()
        
        # Determine refund amounts
        wallet_refund_amount = wallet_txn.amount if wallet_txn else gateway_wallet_amount
        points_refund_amount = points_txn.points if points_txn else gateway_points_used
        
        print(f"Refund Sources:")
        print(f"  Wallet Transaction: {'Found' if wallet_txn else 'Not found'} - NPR {wallet_refund_amount}")
        print(f"  Points Transaction: {'Found' if points_txn else 'Not found'} - {points_refund_amount} points")
        print(f"  Gateway Response: wallet={gateway_wallet_amount}, points={gateway_points_used}")
        
        if wallet_refund_amount <= 0 and points_refund_amount <= 0:
            print(f"❌ Unable to determine refund amounts")
            return False
        
        # Process refunds
        if wallet_refund_amount > 0:
            WalletService().add_balance(user, wallet_refund_amount,
                f'Refund for failed rental {rental.rental_code}')
            print(f"✅ Refunded NPR {wallet_refund_amount} to wallet")
        
        if points_refund_amount > 0:
            award_points(user, points_refund_amount, 'REFUND',
                       f'Refund for failed rental {rental.rental_code}', 
                       async_send=False, related_rental=rental)
            print(f"✅ Refunded {points_refund_amount} points")
        
        # Update transaction and rental status
        txn.status = 'REFUNDED'
        txn.save(update_fields=['status'])
        
        rental.status = 'CANCELLED'
        rental.payment_status = 'REFUNDED'
        rental.save(update_fields=['status', 'payment_status'])
        
        print(f"✅ Updated transaction status to REFUNDED")
        print(f"✅ Updated rental status to CANCELLED")
        
        # STEP 3: Verify final state
        user.wallet.refresh_from_db()
        user_points.refresh_from_db()
        
        final_wallet = user.wallet.balance
        final_points = user_points.current_points
        
        print(f"\n=== FINAL VERIFICATION ===")
        print(f"Final Balances:")
        print(f"  Wallet: NPR {final_wallet}")
        print(f"  Points: {final_points}")
        
        # Check if balances are restored
        wallet_restored = abs(final_wallet - initial_wallet) < Decimal('0.01')
        points_restored = final_points == initial_points
        
        print(f"\nRefund Accuracy:")
        print(f"  Wallet Restored: {'✅' if wallet_restored else '❌'} ({final_wallet} vs {initial_wallet})")
        print(f"  Points Restored: {'✅' if points_restored else '❌'} ({final_points} vs {initial_points})")
        
        # Check final states
        txn.refresh_from_db()
        rental.refresh_from_db()
        
        print(f"\nFinal States:")
        print(f"  Transaction Status: {txn.status}")
        print(f"  Rental Status: {rental.status}")
        print(f"  Payment Status: {rental.payment_status}")
        
        # Overall success check
        success = (
            wallet_restored and 
            points_restored and 
            rental.status == 'CANCELLED' and 
            rental.payment_status == 'REFUNDED' and
            txn.status == 'REFUNDED'
        )
        
        if success:
            print(f"\n🎉 SUCCESS: Popup failure refund working perfectly!")
            print(f"   - Wallet amount refunded to wallet ✅")
            print(f"   - Points amount refunded to points ✅")
            print(f"   - Transaction marked as REFUNDED ✅")
            print(f"   - Rental properly cancelled ✅")
        else:
            print(f"\n❌ FAILED: Some aspect of refund not working correctly")
        
        return success
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            rental.delete()
            print(f"\nCleaned up test rental")
        except:
            pass

if __name__ == "__main__":
    result = simulate_popup_failure_refund()
    print(f"\n{'='*50}")
    print(f"FINAL RESULT: {'PASSED' if result else 'FAILED'}")
    print(f"{'='*50}")
