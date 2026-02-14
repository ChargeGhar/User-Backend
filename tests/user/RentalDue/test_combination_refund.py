#!/usr/bin/env python3
"""
Test PREPAID COMBINATION rental start + popup failure refund
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station
from api.user.payments.models import Transaction, WalletTransaction
from api.user.points.models import PointsTransaction
from api.user.payments.services.rental_payment import RentalPaymentService

User = get_user_model()

def test_combination_payment_and_refund():
    print("=== PREPAID COMBINATION Payment + Refund Test ===\n")
    
    # Get test data
    user = User.objects.get(id=1)
    package = RentalPackage.objects.filter(payment_model='PREPAID', price=50).first()
    
    if not package:
        print("❌ No PREPAID package found")
        return
    
    # Check initial balances
    initial_wallet = user.wallet.balance if hasattr(user, 'wallet') and user.wallet else Decimal('0')
    initial_points = user.user_points.current_points if hasattr(user, 'user_points') and user.user_points else 0
    
    print(f"Initial Balances:")
    print(f"  Wallet: NPR {initial_wallet}")
    print(f"  Points: {initial_points}")
    print(f"Package: {package.name} - NPR {package.price}")
    
    # Test payment breakdown (wallet + points combination)
    payment_breakdown = {
        'wallet_amount': Decimal('30.00'),
        'points_to_use': 200,  # 200 points = NPR 20
        'points_amount': Decimal('20.00')
    }
    
    print(f"\nPayment Breakdown:")
    print(f"  Wallet: NPR {payment_breakdown['wallet_amount']}")
    print(f"  Points: {payment_breakdown['points_to_use']} ({payment_breakdown['points_amount']} NPR)")
    print(f"  Total: NPR {payment_breakdown['wallet_amount'] + payment_breakdown['points_amount']}")
    
    # Create a dummy rental for testing
    station = Station.objects.filter(status='ONLINE').first()
    if not station:
        print("❌ No online station found")
        return
    
    rental = Rental.objects.create(
        user=user,
        station=station,
        package=package,
        rental_code=f"TEST-{user.id}-COMBO",
        status='PENDING_POPUP',
        amount_paid=Decimal('0'),
        payment_status='PENDING'
    )
    
    print(f"\nCreated test rental: {rental.rental_code}")
    
    try:
        # Process payment
        service = RentalPaymentService()
        txn = service.process_rental_payment(user, rental, payment_breakdown)
        
        print(f"\n=== Payment Processed ===")
        print(f"Transaction ID: {txn.transaction_id}")
        print(f"Payment Method: {txn.payment_method_type}")
        print(f"Amount: NPR {txn.amount}")
        print(f"Status: {txn.status}")
        print(f"Gateway Response: {txn.gateway_response}")
        
        # Check balances after payment
        user.refresh_from_db()
        user.wallet.refresh_from_db()
        user.user_points.refresh_from_db()
        
        after_payment_wallet = user.wallet.balance
        after_payment_points = user.user_points.current_points
        
        print(f"\nBalances After Payment:")
        print(f"  Wallet: NPR {after_payment_wallet} (deducted: {initial_wallet - after_payment_wallet})")
        print(f"  Points: {after_payment_points} (deducted: {initial_points - after_payment_points})")
        
        # Check related transactions
        wallet_txn = WalletTransaction.objects.filter(transaction=txn, transaction_type='DEBIT').first()
        points_txn = PointsTransaction.objects.filter(related_rental=rental, transaction_type='SPENT').first()
        
        print(f"\n=== Related Transactions ===")
        if wallet_txn:
            print(f"Wallet Transaction: NPR {wallet_txn.amount} deducted")
        if points_txn:
            print(f"Points Transaction: {points_txn.points} points deducted")
        
        # Simulate refund (popup failure)
        print(f"\n=== Simulating Refund ===")
        
        # Get refund amounts from gateway_response
        gateway_response = txn.gateway_response or {}
        gateway_wallet_amount = Decimal(str(gateway_response.get('wallet_amount', '0')))
        gateway_points_used = int(gateway_response.get('points_used', 0))
        
        print(f"Gateway Response Refund Data:")
        print(f"  Wallet Amount: NPR {gateway_wallet_amount}")
        print(f"  Points Used: {gateway_points_used}")
        
        # Get refund amounts from actual transactions
        wallet_refund_amount = wallet_txn.amount if wallet_txn else gateway_wallet_amount
        points_refund_amount = points_txn.points if points_txn else gateway_points_used
        
        print(f"\nActual Refund Amounts:")
        print(f"  Wallet Refund: NPR {wallet_refund_amount}")
        print(f"  Points Refund: {points_refund_amount}")
        
        # Process refund
        if wallet_refund_amount > 0:
            from api.user.payments.services import WalletService
            WalletService().add_balance(user, wallet_refund_amount, f'Test refund for {rental.rental_code}')
        
        if points_refund_amount > 0:
            from api.user.points.services import award_points
            award_points(user, points_refund_amount, 'REFUND', f'Test refund for {rental.rental_code}', 
                        async_send=False, related_rental=rental)
        
        # Check final balances
        user.refresh_from_db()
        user.wallet.refresh_from_db()
        user.user_points.refresh_from_db()
        
        final_wallet = user.wallet.balance
        final_points = user.user_points.current_points
        
        print(f"\n=== Final Balances ===")
        print(f"  Wallet: NPR {final_wallet}")
        print(f"  Points: {final_points}")
        
        # Verify refund accuracy
        wallet_restored = abs(final_wallet - initial_wallet) < Decimal('0.01')
        points_restored = final_points == initial_points
        
        print(f"\n=== Refund Verification ===")
        print(f"  Wallet Restored: {'✅' if wallet_restored else '❌'} ({final_wallet} vs {initial_wallet})")
        print(f"  Points Restored: {'✅' if points_restored else '❌'} ({final_points} vs {initial_points})")
        
        if wallet_restored and points_restored:
            print(f"\n🎉 SUCCESS: COMBINATION payment and refund working correctly!")
        else:
            print(f"\n❌ FAILED: Refund not accurate")
        
        return wallet_restored and points_restored
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        rental.delete()
        print(f"\nCleaned up test rental")

if __name__ == "__main__":
    test_combination_payment_and_refund()
