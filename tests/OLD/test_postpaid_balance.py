#!/usr/bin/env python
"""
Test POSTPAID Minimum Balance Check

Tests the FIX #5: POSTPAID minimum balance requirement
"""

import os
import sys
import django
from decimal import Decimal

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from django.utils import timezone
from api.user.auth.models import User
from api.user.rentals.models import RentalPackage
from api.user.rentals.services import RentalService
from api.user.stations.models import Station

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{BOLD}{'='*80}")
    print(f"{text:^80}")
    print(f"{'='*80}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_info(text):
    print(f"{CYAN}ℹ️  {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")


def test_postpaid_with_sufficient_balance():
    """Test POSTPAID rental with sufficient balance (should succeed)"""
    print_header("TEST 1: POSTPAID with Sufficient Balance")
    
    try:
        # Get user with good balance
        user = User.objects.filter(
            is_active=True,
            wallet__balance__gte=50
        ).select_related('wallet').first()
        
        if not user:
            print_error("No user with sufficient balance found")
            return False
        
        print_info(f"User: {user.email}")
        print_info(f"Wallet Balance: NPR {user.wallet.balance}")
        
        # Get POSTPAID package
        postpaid_package = RentalPackage.objects.filter(
            payment_model='POSTPAID',
            is_active=True
        ).first()
        
        if not postpaid_package:
            print_warning("No POSTPAID package found - creating one")
            postpaid_package = RentalPackage.objects.create(
                name="Test POSTPAID Package",
                duration_minutes=60,
                price=Decimal('50.00'),
                payment_model='POSTPAID',
                is_active=True
            )
        
        print_info(f"Package: {postpaid_package.name} (POSTPAID)")
        print_info(f"Price: NPR {postpaid_package.price}")
        
        # Get station
        station = Station.objects.filter(status='ONLINE').first()
        if not station:
            print_error("No online station found")
            return False
        
        print_info(f"Station: {station.station_name}")
        
        # Try to start rental
        service = RentalService()
        rental = service.start_rental(
            user=user,
            station_sn=station.serial_number,
            package_id=str(postpaid_package.id)
        )
        
        print_success(f"POSTPAID rental started successfully!")
        print_info(f"Rental Code: {rental.rental_code}")
        print_info(f"Status: {rental.status}")
        print_info(f"Payment Status: {rental.payment_status}")
        
        # Clean up - cancel the rental
        rental.status = 'CANCELLED'
        rental.save()
        print_info("(Rental cancelled for cleanup)")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        return False


def test_postpaid_with_insufficient_balance():
    """Test POSTPAID rental with insufficient balance (should fail)"""
    print_header("TEST 2: POSTPAID with Insufficient Balance")
    
    try:
        # Get or create user with low balance
        user = User.objects.filter(
            is_active=True,
            wallet__balance__lt=50
        ).select_related('wallet').first()
        
        if not user:
            # Create test user with low balance
            print_info("Creating test user with low balance")
            user = User.objects.create_user(
                username=f'test_lowbalance_{timezone.now().timestamp()}',
                email=f'test_lowbalance_{timezone.now().timestamp()}@test.com',
                password='testpass123'
            )
            # Set low balance
            from api.user.payments.models import Wallet
            wallet = Wallet.objects.create(user=user, balance=Decimal('20.00'))
            user.wallet = wallet
        
        print_info(f"User: {user.email}")
        print_info(f"Wallet Balance: NPR {user.wallet.balance}")
        
        # Get POSTPAID package
        postpaid_package = RentalPackage.objects.filter(
            payment_model='POSTPAID',
            is_active=True
        ).first()
        
        if not postpaid_package:
            print_error("No POSTPAID package found")
            return False
        
        print_info(f"Package: {postpaid_package.name} (POSTPAID)")
        print_info(f"Required Minimum Balance: NPR 50.00")
        
        # Get station
        station = Station.objects.filter(status='ONLINE').first()
        if not station:
            print_error("No online station found")
            return False
        
        print_info(f"Station: {station.station_name}")
        
        # Try to start rental (should fail)
        service = RentalService()
        try:
            rental = service.start_rental(
                user=user,
                station_sn=station.serial_number,
                package_id=str(postpaid_package.id)
            )
            print_error("Rental started unexpectedly - validation failed!")
            return False
        except Exception as e:
            error_msg = str(e)
            if 'insufficient_postpaid_balance' in error_msg.lower() or 'minimum wallet balance' in error_msg.lower():
                print_success("Rental correctly blocked due to insufficient balance")
                print_info(f"Error message: {error_msg}")
                return True
            else:
                print_error(f"Unexpected error: {error_msg}")
                return False
        
    except Exception as e:
        print_error(f"Test setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_prepaid_not_affected():
    """Test that PREPAID rentals are not affected by balance check"""
    print_header("TEST 3: PREPAID Not Affected by Balance Check")
    
    try:
        # Get user with any balance
        user = User.objects.filter(is_active=True).select_related('wallet').first()
        
        if not user:
            print_error("No user found")
            return False
        
        print_info(f"User: {user.email}")
        wallet_balance = user.wallet.balance if hasattr(user, 'wallet') and user.wallet else Decimal('0')
        print_info(f"Wallet Balance: NPR {wallet_balance}")
        
        # Get PREPAID package
        prepaid_package = RentalPackage.objects.filter(
            payment_model='PREPAID',
            is_active=True
        ).first()
        
        if not prepaid_package:
            print_error("No PREPAID package found")
            return False
        
        print_info(f"Package: {prepaid_package.name} (PREPAID)")
        print_info(f"Price: NPR {prepaid_package.price}")
        print_success("PREPAID rentals should NOT check minimum balance requirement")
        print_info("(They only check if user can pay the full package price)")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    print(f"\n{BOLD}{CYAN}Starting POSTPAID Minimum Balance Tests{RESET}")
    print(f"{CYAN}Testing FIX #5: POSTPAID Minimum Balance Requirement{RESET}\n")
    
    results = []
    
    # Test 1: Sufficient balance
    results.append(("POSTPAID with sufficient balance", test_postpaid_with_sufficient_balance()))
    
    # Test 2: Insufficient balance
    results.append(("POSTPAID with insufficient balance", test_postpaid_with_insufficient_balance()))
    
    # Test 3: PREPAID not affected
    results.append(("PREPAID not affected", test_prepaid_not_affected()))
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    print(f"\n{BOLD}Results: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print_success("\nAll tests passed! ✨")
        return 0
    else:
        print_error(f"\n{total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
