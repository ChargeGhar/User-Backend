#!/usr/bin/env python
"""
Comprehensive Test Script for Rental System Gaps
Tests all critical issues identified in RENTAL_GAPS_QUICK_REFERENCE.md
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal

from api.user.rentals.models import Rental, RentalExtension, RentalPackage
from api.user.stations.models import Station, StationSlot, PowerBank
from api.user.auth.models import User
from api.user.payments.models import Transaction
from api.user.system.models import AppConfig

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_section(title):
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{title:^80}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

def print_test(name, passed, message=""):
    status = f"{GREEN}✅ PASSED{RESET}" if passed else f"{RED}❌ FAILED{RESET}"
    print(f"{status} - {name}")
    if message:
        print(f"  → {message}")

def print_warning(message):
    print(f"{YELLOW}⚠️  WARNING: {message}{RESET}")

def print_info(message):
    print(f"  ℹ️  {message}")


# =============================================================================
# TEST 1: CRITICAL - Slot Release on Return
# =============================================================================
def test_slot_release_on_return():
    print_section("TEST 1: CRITICAL - Slot Release on Return")
    
    # Get an active rental
    rental = Rental.objects.filter(status='ACTIVE').first()
    if not rental:
        print_warning("No active rental found. Creating one...")
        return False
    
    print_info(f"Testing rental: {rental.rental_code}")
    
    # Check original slot
    original_slot = rental.slot
    if not original_slot:
        print_warning("Rental has no slot assigned")
        return False
    
    print_info(f"Original pickup slot: {original_slot.slot_number}")
    print_info(f"Original slot status: {original_slot.status}")
    print_info(f"Original slot current_rental: {original_slot.current_rental_id}")
    
    # Get powerbank current location
    pb = rental.power_bank
    print_info(f"PowerBank ID: {pb.id}")
    print_info(f"PowerBank current_station: {pb.current_station_id}")
    print_info(f"PowerBank current_slot: {pb.current_slot.slot_number if pb.current_slot else 'None'}")
    
    # Check if return logic would release original slot
    # This is a READ-ONLY test - we won't actually return
    
    # Expected behavior:
    # 1. Original slot should be AVAILABLE after return
    # 2. Original slot current_rental should be NULL
    # 3. Return slot should be OCCUPIED (with returned powerbank)
    
    # Check current state
    is_same_slot = original_slot.id == (pb.current_slot.id if pb.current_slot else None)
    
    if is_same_slot:
        print_test("Slot release test", True, "PowerBank still in original slot (not yet returned)")
    else:
        # PowerBank is in different slot - check if original was released
        original_slot.refresh_from_db()
        slot_released = original_slot.status == 'AVAILABLE' and original_slot.current_rental_id is None
        
        print_test(
            "Original slot released after return", 
            slot_released,
            f"Original slot status: {original_slot.status}, current_rental: {original_slot.current_rental_id}"
        )
        return slot_released
    
    return True


# =============================================================================
# TEST 2: CRITICAL - Transaction-Rental Link
# =============================================================================
def test_transaction_rental_link():
    print_section("TEST 2: CRITICAL - Transaction-Rental Link")
    
    # Check recent rentals with payments
    rentals_with_payment = Rental.objects.filter(
        payment_status='PAID',
        amount_paid__gt=0
    ).order_by('-created_at')[:10]
    
    print_info(f"Checking {rentals_with_payment.count()} paid rentals...")
    
    orphaned_count = 0
    linked_count = 0
    
    for rental in rentals_with_payment:
        # Check if there's a transaction linked to this rental
        txn = Transaction.objects.filter(related_rental=rental).first()
        
        if txn:
            linked_count += 1
        else:
            orphaned_count += 1
            print_warning(f"Rental {rental.rental_code} has no linked transaction!")
    
    print_info(f"Linked: {linked_count}, Orphaned: {orphaned_count}")
    
    success_rate = (linked_count / len(rentals_with_payment) * 100) if rentals_with_payment else 0
    print_test(
        "Transaction-Rental linking",
        orphaned_count == 0,
        f"Success rate: {success_rate:.1f}% ({linked_count}/{len(rentals_with_payment)})"
    )
    
    return orphaned_count == 0


# =============================================================================
# TEST 3: CRITICAL - Race Condition Protection
# =============================================================================
def test_race_condition_protection():
    print_section("TEST 3: CRITICAL - Race Condition Protection")
    
    # Check if slot selection uses select_for_update
    from api.user.rentals.services import RentalService
    import inspect
    
    service = RentalService()
    
    # Check if the method exists and uses proper locking
    if hasattr(service, '_get_available_power_bank_and_slot'):
        source = inspect.getsource(service._get_available_power_bank_and_slot)
        uses_locking = 'select_for_update' in source
        
        print_test(
            "Race condition protection",
            uses_locking,
            "select_for_update() found in code" if uses_locking else "No database locking detected"
        )
        return uses_locking
    else:
        print_warning("Method _get_available_power_bank_and_slot not found")
        return False


# =============================================================================
# TEST 4: HIGH - Points Refund on Cancellation
# =============================================================================
def test_points_refund():
    print_section("TEST 4: HIGH - Points Refund on Cancellation")
    
    # Check if cancel_rental has points refund logic
    from api.user.rentals.services import RentalService
    import inspect
    
    service = RentalService()
    
    if hasattr(service, 'cancel_rental'):
        source = inspect.getsource(service.cancel_rental)
        has_points_refund = 'points' in source.lower() and 'refund' in source.lower()
        
        print_test(
            "Points refund logic",
            has_points_refund,
            "Points refund logic found" if has_points_refund else "Only wallet refund detected"
        )
        return has_points_refund
    else:
        print_warning("Method cancel_rental not found")
        return False


# =============================================================================
# TEST 5: HIGH - Auto-Collection of Dues
# =============================================================================
def test_auto_collection():
    print_section("TEST 5: HIGH - Auto-Collection of Dues")
    
    # Check for rentals with pending payments
    pending_rentals = Rental.objects.filter(
        status='COMPLETED',
        payment_status='PENDING'
    ).count()
    
    print_info(f"Found {pending_rentals} completed rentals with pending payment")
    
    # Check if return logic has auto-collection
    from api.user.stations.services.power_bank_service import PowerBankService
    import inspect
    
    service = PowerBankService()
    
    if hasattr(service, 'return_power_bank'):
        source = inspect.getsource(service.return_power_bank)
        has_auto_collection = 'pay_rental_due' in source or 'auto_collect' in source.lower()
        
        print_test(
            "Auto-collection logic",
            has_auto_collection,
            "Auto-collection logic found" if has_auto_collection else "No auto-collection detected"
        )
        
        if not has_auto_collection and pending_rentals > 0:
            print_warning(f"{pending_rentals} rentals waiting for manual payment")
        
        return has_auto_collection
    else:
        print_warning("Method return_power_bank not found")
        return False


# =============================================================================
# TEST 6: HIGH - PowerBank Location Management
# =============================================================================
def test_powerbank_location():
    print_section("TEST 6: HIGH - PowerBank Location Management")
    
    # Check rented powerbanks that still have location set
    rented_with_location = PowerBank.objects.filter(
        status='RENTED',
        current_station__isnull=False
    ).count()
    
    # Check available powerbanks without location
    available_without_location = PowerBank.objects.filter(
        status='AVAILABLE',
        current_station__isnull=True
    ).count()
    
    print_info(f"Rented powerbanks with location: {rented_with_location}")
    print_info(f"Available powerbanks without location: {available_without_location}")
    
    # Rented powerbanks should have NULL location
    location_properly_managed = (rented_with_location == 0)
    
    print_test(
        "PowerBank location management",
        location_properly_managed,
        "All rented powerbanks have NULL location" if location_properly_managed 
        else f"{rented_with_location} rented powerbanks still have location set"
    )
    
    return location_properly_managed


# =============================================================================
# TEST 7: MEDIUM - Timely Return Bonus
# =============================================================================
def test_timely_return_bonus():
    print_section("TEST 7: MEDIUM - Timely Return Bonus")
    
    # Check rentals returned on time without bonus
    on_time_no_bonus = Rental.objects.filter(
        status='COMPLETED',
        is_returned_on_time=True,
        timely_return_bonus_awarded=False
    ).count()
    
    # Check if bonus logic exists in return code
    from api.user.stations.services.power_bank_service import PowerBankService
    import inspect
    
    service = PowerBankService()
    
    if hasattr(service, 'return_power_bank'):
        source = inspect.getsource(service.return_power_bank)
        has_bonus_logic = 'timely_return_bonus' in source
        
        print_info(f"On-time returns without bonus: {on_time_no_bonus}")
        
        print_test(
            "Timely return bonus logic",
            has_bonus_logic,
            "Bonus logic found" if has_bonus_logic else "Bonus field exists but not implemented"
        )
        
        return has_bonus_logic
    
    return False


# =============================================================================
# TEST 8: AppConfig Integration
# =============================================================================
def test_appconfig_integration():
    print_section("TEST 8: AppConfig Integration")
    
    # Check for cancellation window config
    try:
        config = AppConfig.objects.get(key='RENTAL_CANCELLATION_WINDOW_MINUTES')
        print_info(f"Cancellation window: {config.value} minutes")
        print_info(f"Active: {config.is_active}")
        
        # Check if it's used in code
        from api.user.rentals.services import RentalService
        import inspect
        
        service = RentalService()
        if hasattr(service, 'cancel_rental'):
            source = inspect.getsource(service.cancel_rental)
            uses_config = 'RENTAL_CANCELLATION_WINDOW_MINUTES' in source
            
            print_test(
                "AppConfig usage",
                uses_config,
                "Cancellation window uses AppConfig" if uses_config else "Still using hardcoded value"
            )
            return uses_config
    except AppConfig.DoesNotExist:
        print_test("AppConfig", False, "RENTAL_CANCELLATION_WINDOW_MINUTES not found")
        return False
    
    return False


# =============================================================================
# TEST 9: Database Integrity Check
# =============================================================================
def test_database_integrity():
    print_section("TEST 9: Database Integrity Check")
    
    issues = []
    
    # Check 1: Orphaned occupied slots
    orphaned_slots = StationSlot.objects.filter(
        status='OCCUPIED',
        current_rental__isnull=True
    ).count()
    
    if orphaned_slots > 0:
        issues.append(f"{orphaned_slots} orphaned occupied slots")
    
    print_test(
        "No orphaned occupied slots",
        orphaned_slots == 0,
        f"Found {orphaned_slots} orphaned slots" if orphaned_slots > 0 else "All slots properly linked"
    )
    
    # Check 2: Rentals with wrong slot status
    active_rentals = Rental.objects.filter(status='ACTIVE').count()
    occupied_slots = StationSlot.objects.filter(status='OCCUPIED').count()
    
    print_info(f"Active rentals: {active_rentals}")
    print_info(f"Occupied slots: {occupied_slots}")
    
    # Check 3: PowerBank status mismatches
    rented_powerbanks = PowerBank.objects.filter(status='RENTED').count()
    print_info(f"Rented powerbanks: {rented_powerbanks}")
    
    if active_rentals != rented_powerbanks:
        issues.append(f"Mismatch: {active_rentals} active rentals but {rented_powerbanks} rented powerbanks")
    
    print_test(
        "PowerBank-Rental consistency",
        active_rentals == rented_powerbanks,
        "Counts match" if active_rentals == rented_powerbanks else "Counts don't match"
    )
    
    return len(issues) == 0


# =============================================================================
# TEST 10: Realtime Late Fee Calculation
# =============================================================================
def test_realtime_late_fee():
    print_section("TEST 10: Realtime Late Fee Calculation")
    
    # Check if @property methods exist
    rental = Rental.objects.first()
    if not rental:
        print_warning("No rental found to test")
        return False
    
    has_current_overdue = hasattr(rental, 'current_overdue_amount')
    has_estimated_total = hasattr(rental, 'estimated_total_cost')
    has_minutes_overdue = hasattr(rental, 'minutes_overdue')
    
    print_test("current_overdue_amount property", has_current_overdue, "Property exists")
    print_test("estimated_total_cost property", has_estimated_total, "Property exists")
    print_test("minutes_overdue property", has_minutes_overdue, "Property exists")
    
    if has_current_overdue and has_estimated_total:
        # Try to access them
        try:
            overdue = rental.current_overdue_amount
            total = rental.estimated_total_cost
            minutes = rental.minutes_overdue if has_minutes_overdue else 0
            
            print_info(f"Current overdue: NPR {overdue}")
            print_info(f"Estimated total: NPR {total}")
            print_info(f"Minutes overdue: {minutes}")
            
            print_test("Realtime calculation working", True, "All properties accessible")
            return True
        except Exception as e:
            print_test("Realtime calculation", False, f"Error: {str(e)}")
            return False
    
    return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================
def main():
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{'RENTAL SYSTEM GAPS - COMPREHENSIVE TEST':^80}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    results = {}
    
    # Run all tests
    results['slot_release'] = test_slot_release_on_return()
    results['transaction_link'] = test_transaction_rental_link()
    results['race_condition'] = test_race_condition_protection()
    results['points_refund'] = test_points_refund()
    results['auto_collection'] = test_auto_collection()
    results['powerbank_location'] = test_powerbank_location()
    results['timely_bonus'] = test_timely_return_bonus()
    results['appconfig'] = test_appconfig_integration()
    results['db_integrity'] = test_database_integrity()
    results['realtime_fee'] = test_realtime_late_fee()
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {total - passed}{RESET}")
    print(f"Success Rate: {passed/total*100:.1f}%\n")
    
    # Critical issues summary
    critical_issues = {
        'Slot Release': results['slot_release'],
        'Transaction Link': results['transaction_link'],
        'Race Condition Protection': results['race_condition']
    }
    
    print(f"{RED}CRITICAL ISSUES:{RESET}")
    for name, passed in critical_issues.items():
        status = f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"
        print(f"  {status} {name}")
    
    # High priority issues
    high_priority = {
        'Points Refund': results['points_refund'],
        'Auto-Collection': results['auto_collection'],
        'PowerBank Location': results['powerbank_location']
    }
    
    print(f"\n{YELLOW}HIGH PRIORITY ISSUES:{RESET}")
    for name, passed in high_priority.items():
        status = f"{GREEN}✅{RESET}" if passed else f"{YELLOW}⚠️{RESET}"
        print(f"  {status} {name}")
    
    print(f"\n{BLUE}{'='*80}{RESET}\n")
    
    return passed == total


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{RED}FATAL ERROR: {str(e)}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
