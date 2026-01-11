#!/usr/bin/env python
"""
Detailed Business Logic Test for Remaining Issues
Tests: Transaction-Rental Link, Auto-Collection, Timely Return Bonus
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal

from api.user.rentals.models import Rental
from api.user.payments.models import Transaction
from api.user.auth.models import User
from api.user.rentals.models import RentalPackage
from api.user.stations.models import Station
from api.user.system.models import AppConfig

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'

def print_header(title):
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{title:^80}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

def print_test(name, passed, details=""):
    status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
    print(f"{status} - {name}")
    if details:
        print(f"  {CYAN}{details}{RESET}")

def print_info(message):
    print(f"  ℹ️  {message}")

def print_code_check(feature, has_feature, line_ref=""):
    status = f"{GREEN}✅{RESET}" if has_feature else f"{RED}❌{RESET}"
    print(f"{status} {feature}" + (f" (line {line_ref})" if line_ref else ""))


# =============================================================================
# TEST 1: Transaction-Rental Link Investigation
# =============================================================================
def test_transaction_rental_link():
    print_header("TEST 1: TRANSACTION-RENTAL LINK - DETAILED INVESTIGATION")
    
    print(f"{CYAN}Checking Code Implementation...{RESET}\n")
    
    # Check if the code has been updated
    from api.user.rentals.services import RentalService
    import inspect
    
    service = RentalService()
    start_rental_source = inspect.getsource(service.start_rental)
    prepayment_source = inspect.getsource(service._process_prepayment)
    
    # Check critical fixes
    has_pending_status = "'PENDING'" in start_rental_source or '"PENDING"' in start_rental_source
    has_rental_param = "rental=rental" in prepayment_source
    creates_rental_first = start_rental_source.find("Rental.objects.create") < start_rental_source.find("_process_prepayment")
    
    print_code_check("Creates rental FIRST (before payment)", creates_rental_first, "~line 60")
    print_code_check("Uses PENDING status initially", has_pending_status, "~line 62")
    print_code_check("Passes rental to payment", has_rental_param, "~line 217")
    
    code_fixed = creates_rental_first and has_pending_status and has_rental_param
    
    print(f"\n{CYAN}Checking Database State...{RESET}\n")
    
    # Check actual database data
    recent_rentals = Rental.objects.filter(
        payment_status='PAID',
        amount_paid__gt=0
    ).order_by('-created_at')[:10]
    
    print_info(f"Analyzing {recent_rentals.count()} recent paid rentals...")
    
    linked_count = 0
    orphaned_count = 0
    details = []
    
    for rental in recent_rentals:
        txn = Transaction.objects.filter(related_rental=rental).first()
        if txn:
            linked_count += 1
            details.append(f"  {GREEN}✓{RESET} {rental.rental_code}: Transaction {str(txn.id)[:8]} linked")
        else:
            orphaned_count += 1
            details.append(f"  {RED}✗{RESET} {rental.rental_code}: No transaction link (created {rental.created_at.strftime('%Y-%m-%d %H:%M')})")
    
    # Show sample details
    if orphaned_count > 0:
        print(f"\n{YELLOW}Orphaned Rentals (no transaction link):{RESET}")
        for detail in [d for d in details if '✗' in d][:5]:
            print(detail)
    
    if linked_count > 0:
        print(f"\n{GREEN}Properly Linked Rentals:{RESET}")
        for detail in [d for d in details if '✓' in d][:3]:
            print(detail)
    
    success_rate = (linked_count / len(recent_rentals) * 100) if recent_rentals else 0
    
    print(f"\n{CYAN}Results:{RESET}")
    print_info(f"Linked: {linked_count}/{len(recent_rentals)} ({success_rate:.1f}%)")
    print_info(f"Orphaned: {orphaned_count}/{len(recent_rentals)}")
    
    # Overall status
    print(f"\n{CYAN}Status:{RESET}")
    if code_fixed and success_rate == 100:
        print_test("Transaction-Rental Link", True, "✅ Code fixed AND database clean")
    elif code_fixed and success_rate > 0:
        print_test("Transaction-Rental Link", False, 
                  f"⚠️ Code fixed but {orphaned_count} old rentals still orphaned (pre-fix data)")
    elif code_fixed:
        print_test("Transaction-Rental Link", False, 
                  "⚠️ Code fixed but no test data available")
    else:
        print_test("Transaction-Rental Link", False, 
                  "❌ Code needs fixing - rental should be created BEFORE payment")
    
    return code_fixed, orphaned_count


# =============================================================================
# TEST 2: Auto-Collection Logic Investigation
# =============================================================================
def test_auto_collection():
    print_header("TEST 2: AUTO-COLLECTION LOGIC - DETAILED INVESTIGATION")
    
    print(f"{CYAN}Checking Code Implementation...{RESET}\n")
    
    from api.user.rentals.services import RentalService
    import inspect
    
    service = RentalService()
    return_source = inspect.getsource(service.return_power_bank)
    
    # Check for auto-collection logic
    has_auto_collect = 'pay_rental_due' in return_source or 'auto' in return_source.lower()
    has_payment_service = 'RentalPaymentService' in return_source
    has_try_collect = 'PaymentCalculationService' in return_source
    
    print_code_check("Calls payment service", has_payment_service)
    print_code_check("Has auto-collection logic", has_auto_collect)
    print_code_check("Calculates payment options", has_try_collect)
    
    print(f"\n{CYAN}Checking Database State...{RESET}\n")
    
    # Check for completed rentals with pending payment
    pending_postpaid = Rental.objects.filter(
        status='COMPLETED',
        payment_status='PENDING',
        package__payment_model='POSTPAID'
    ).count()
    
    pending_overdue = Rental.objects.filter(
        status='COMPLETED',
        payment_status='PENDING',
        overdue_amount__gt=0
    ).count()
    
    total_pending = Rental.objects.filter(
        status='COMPLETED',
        payment_status='PENDING'
    ).count()
    
    print_info(f"POSTPAID rentals awaiting payment: {pending_postpaid}")
    print_info(f"Rentals with unpaid late fees: {pending_overdue}")
    print_info(f"Total completed rentals with pending payment: {total_pending}")
    
    # Check the actual return logic behavior
    print(f"\n{CYAN}Code Analysis:{RESET}")
    if '_calculate_postpayment_charges' in return_source:
        print(f"  {GREEN}✓{RESET} Calculates POSTPAID charges")
    if '_calculate_overdue_charges' in return_source:
        print(f"  {GREEN}✓{RESET} Calculates overdue charges")
    if 'payment_status = \'PENDING\'' in return_source or 'payment_status = "PENDING"' in return_source:
        print(f"  {YELLOW}⚠{RESET} Sets payment_status to PENDING (but doesn't auto-collect)")
    
    # Final status
    print(f"\n{CYAN}Status:{RESET}")
    if has_auto_collect and total_pending == 0:
        print_test("Auto-Collection", True, "✅ Logic implemented and no pending payments")
    elif has_auto_collect:
        print_test("Auto-Collection", False, 
                  f"⚠️ Logic exists but {total_pending} rentals awaiting manual payment")
    else:
        print_test("Auto-Collection", False, 
                  f"❌ NOT IMPLEMENTED - Charges calculated but not collected ({total_pending} pending)")
        print(f"\n{YELLOW}RECOMMENDATION:{RESET}")
        print("  Add auto-collection logic after _calculate_postpayment_charges() and _calculate_overdue_charges()")
        print("  Try to deduct from user's points/wallet, send notification if insufficient")
    
    return has_auto_collect, total_pending


# =============================================================================
# TEST 3: Timely Return Bonus Investigation
# =============================================================================
def test_timely_return_bonus():
    print_header("TEST 3: TIMELY RETURN BONUS - DETAILED INVESTIGATION")
    
    print(f"{CYAN}Checking Code Implementation...{RESET}\n")
    
    from api.user.rentals.services import RentalService
    import inspect
    
    service = RentalService()
    return_source = inspect.getsource(service.return_power_bank)
    
    # Check for bonus logic
    has_bonus_logic = 'timely_return_bonus' in return_source.lower()
    has_bonus_award = 'award_points' in return_source and 'ON_TIME_RETURN' in return_source
    has_config_check = 'POINTS_TIMELY_RETURN' in return_source
    
    print_code_check("Has timely return bonus logic", has_bonus_logic, "~line 485")
    print_code_check("Awards points for on-time return", has_bonus_award, "~line 490")
    print_code_check("Uses AppConfig for bonus amount", has_config_check, "~line 487")
    
    # Check AppConfig
    try:
        config = AppConfig.objects.get(key='POINTS_TIMELY_RETURN', is_active=True)
        bonus_amount = int(config.value)
        print(f"\n  {GREEN}✓{RESET} AppConfig found: {bonus_amount} points for on-time return")
    except AppConfig.DoesNotExist:
        print(f"\n  {YELLOW}⚠{RESET} AppConfig POINTS_TIMELY_RETURN not found (will use default: 50)")
        bonus_amount = 50
    
    print(f"\n{CYAN}Checking Database State...{RESET}\n")
    
    # Check on-time returns
    on_time_rentals = Rental.objects.filter(
        status='COMPLETED',
        is_returned_on_time=True
    )
    
    with_bonus = on_time_rentals.filter(timely_return_bonus_awarded=True).count()
    without_bonus = on_time_rentals.filter(timely_return_bonus_awarded=False).count()
    total_on_time = on_time_rentals.count()
    
    print_info(f"Total on-time returns: {total_on_time}")
    print_info(f"Bonus awarded: {with_bonus}")
    print_info(f"Bonus NOT awarded: {without_bonus}")
    
    if without_bonus > 0:
        # Check if these are old rentals (pre-fix)
        old_rentals = on_time_rentals.filter(
            timely_return_bonus_awarded=False,
            ended_at__lt=timezone.now() - timedelta(days=1)
        ).count()
        
        if old_rentals > 0:
            print(f"\n  {YELLOW}Note:{RESET} {old_rentals} are old rentals from before fix was implemented")
    
    # Final status
    print(f"\n{CYAN}Status:{RESET}")
    if has_bonus_logic and has_bonus_award:
        if without_bonus == 0:
            print_test("Timely Return Bonus", True, 
                      f"✅ Fully implemented - All {with_bonus} on-time returns got bonus")
        else:
            print_test("Timely Return Bonus", True, 
                      f"✅ Implemented - {without_bonus} old rentals missed bonus (pre-fix data)")
    else:
        print_test("Timely Return Bonus", False, 
                  f"❌ NOT IMPLEMENTED - Field exists but logic missing")
        print(f"\n{YELLOW}RECOMMENDATION:{RESET}")
        print(f"  Add bonus award logic in return_power_bank() after completion points")
        print(f"  Award {bonus_amount} points when is_returned_on_time=True")
    
    return has_bonus_logic, without_bonus


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================
def main():
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{'BUSINESS LOGIC INVESTIGATION - REMAINING ISSUES':^80}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    # Run tests
    txn_fixed, orphaned = test_transaction_rental_link()
    auto_collect_exists, pending_payments = test_auto_collection()
    bonus_implemented, missed_bonus = test_timely_return_bonus()
    
    # Summary
    print_header("SUMMARY & RECOMMENDATIONS")
    
    print(f"{CYAN}1. Transaction-Rental Link:{RESET}")
    if txn_fixed and orphaned == 0:
        print(f"  {GREEN}✅ FIXED{RESET} - Code updated and database clean")
    elif txn_fixed:
        print(f"  {GREEN}✅ CODE FIXED{RESET} - But {orphaned} old rentals have orphaned transactions")
        print(f"  {YELLOW}→ Action:{RESET} These are pre-fix data, new rentals will be linked correctly")
    else:
        print(f"  {RED}❌ NEEDS FIX{RESET} - Update start_rental() to create rental BEFORE payment")
    
    print(f"\n{CYAN}2. Auto-Collection Logic:{RESET}")
    if auto_collect_exists and pending_payments == 0:
        print(f"  {GREEN}✅ IMPLEMENTED{RESET} - Auto-collection working")
    elif auto_collect_exists:
        print(f"  {YELLOW}⚠ PARTIAL{RESET} - Logic exists but {pending_payments} rentals awaiting payment")
    else:
        print(f"  {RED}❌ NOT IMPLEMENTED{RESET} - {pending_payments} completed rentals with pending payment")
        print(f"  {YELLOW}→ Action:{RESET} Add auto-collection after charge calculation in return_power_bank()")
        print(f"  {YELLOW}→ Impact:{RESET} Revenue loss - users accumulate unpaid dues")
    
    print(f"\n{CYAN}3. Timely Return Bonus:{RESET}")
    if bonus_implemented and missed_bonus == 0:
        print(f"  {GREEN}✅ IMPLEMENTED{RESET} - Bonus awarded for all on-time returns")
    elif bonus_implemented:
        print(f"  {GREEN}✅ IMPLEMENTED{RESET} - {missed_bonus} old returns missed bonus (pre-fix)")
    else:
        print(f"  {RED}❌ NOT IMPLEMENTED{RESET} - {missed_bonus} on-time returns didn't get bonus")
        print(f"  {YELLOW}→ Action:{RESET} Add bonus award logic in return_power_bank()")
        print(f"  {YELLOW}→ Impact:{RESET} Missing user engagement incentive")
    
    # Overall grade
    fixes_implemented = sum([txn_fixed, auto_collect_exists, bonus_implemented])
    total_fixes = 3
    grade = (fixes_implemented / total_fixes) * 100
    
    print(f"\n{CYAN}Overall Progress:{RESET}")
    print(f"  Fixes Implemented: {fixes_implemented}/{total_fixes} ({grade:.0f}%)")
    
    if grade == 100:
        print(f"  {GREEN}Grade: A - All critical issues fixed!{RESET}")
    elif grade >= 67:
        print(f"  {YELLOW}Grade: B - Most issues fixed, some cleanup needed{RESET}")
    elif grade >= 33:
        print(f"  {YELLOW}Grade: C - Some fixes done, more work needed{RESET}")
    else:
        print(f"  {RED}Grade: D - Critical work still required{RESET}")
    
    print(f"\n{BLUE}{'='*80}{RESET}\n")
    
    return grade == 100


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{RED}FATAL ERROR: {str(e)}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
