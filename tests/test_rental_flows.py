"""
Complete Rental Business Logic Test Suite
==========================================

Tests all rental flows:
1. Start Rental (PREPAID vs POSTPAID)
2. Pay Overdue
3. Extend Rental
4. Return Flow

Usage:
    python tests/test_rental_flows.py start --email user@example.com --package-id <uuid>
    python tests/test_rental_flows.py extend --rental-code KMWLX6ZT --package-id <uuid>
    python tests/test_rental_flows.py pay-overdue --rental-code KMWLX6ZT
    python tests/test_rental_flows.py complete-flow --email user@example.com
"""

import os
import sys
import django
import argparse
from decimal import Decimal
from datetime import timedelta

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from django.utils import timezone
from django.db import transaction
from api.user.auth.models import User
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station, PowerBank, StationSlot
from api.user.rentals.services import RentalService
from api.user.payments.services import PaymentCalculationService, RentalPaymentService


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_section(title):
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")


def print_success(message):
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")


def print_info(message):
    print(f"{Colors.OKCYAN}ℹ️  {message}{Colors.ENDC}")


def print_warning(message):
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")


def print_error(message):
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")


def print_data(label, value):
    print(f"   {Colors.BOLD}{label}:{Colors.ENDC} {value}")


def get_user(email):
    """Get or create test user"""
    user = User.objects.filter(email=email).first()
    if not user:
        print_error(f"User not found: {email}")
        sys.exit(1)
    return user


def get_rental(rental_code):
    """Get rental by code"""
    rental = Rental.objects.filter(rental_code=rental_code).first()
    if not rental:
        print_error(f"Rental not found: {rental_code}")
        sys.exit(1)
    return rental


def display_user_balances(user):
    """Display user's current balances"""
    print_info("Current Balances:")
    try:
        points = user.points.current_points
        print_data("Points", f"{points} points (≈ NPR {points/10:.2f})")
    except:
        print_data("Points", "0 points")
    
    try:
        wallet = user.wallet.balance
        print_data("Wallet", f"NPR {wallet:.2f}")
    except:
        print_data("Wallet", "NPR 0.00")


def display_rental_info(rental):
    """Display rental information"""
    print_info("Rental Details:")
    print_data("Code", rental.rental_code)
    print_data("Status", rental.status)
    print_data("Payment Status", rental.payment_status)
    print_data("Package", f"{rental.package.name} ({rental.package.payment_model})")
    print_data("Started", rental.started_at.strftime('%Y-%m-%d %H:%M:%S') if rental.started_at else "Not started")
    print_data("Due", rental.due_at.strftime('%Y-%m-%d %H:%M:%S'))
    print_data("Amount Paid", f"NPR {rental.amount_paid:.2f}")
    print_data("Overdue Amount", f"NPR {rental.overdue_amount:.2f}")
    
    if rental.status == 'ACTIVE':
        now = timezone.now()
        if now > rental.due_at:
            overdue_duration = now - rental.due_at
            overdue_minutes = int(overdue_duration.total_seconds() / 60)
            print_warning(f"Overdue by {overdue_minutes} minutes")
        else:
            remaining = rental.due_at - now
            remaining_minutes = int(remaining.total_seconds() / 60)
            print_data("Time Remaining", f"{remaining_minutes} minutes")


def test_start_rental_prepaid(user_email, package_id=None):
    """Test starting a PREPAID rental"""
    print_section("TEST: Start PREPAID Rental")
    
    user = get_user(user_email)
    display_user_balances(user)
    
    # Get or find PREPAID package
    if package_id:
        package = RentalPackage.objects.get(id=package_id)
    else:
        package = RentalPackage.objects.filter(
            payment_model='PREPAID',
            is_active=True
        ).first()
        if not package:
            print_error("No PREPAID package found")
            return
    
    print_info(f"Selected Package: {package.name} - NPR {package.price} ({package.duration_minutes} min)")
    
    # Calculate payment options
    calc_service = PaymentCalculationService()
    options = calc_service.calculate_payment_options(
        user=user,
        scenario='pre_payment',
        package_id=str(package.id)
    )
    
    print_info("Payment Calculation:")
    print_data("Total Amount", f"NPR {options['total_amount']:.2f}")
    print_data("Points to Use", f"{options['payment_breakdown']['points_used']} (NPR {options['payment_breakdown']['points_amount']:.2f})")
    print_data("Wallet to Use", f"NPR {options['payment_breakdown']['wallet_used']:.2f}")
    print_data("Sufficient Funds", "YES ✅" if options['is_sufficient'] else f"NO ❌ (Shortfall: NPR {options['shortfall']:.2f})")
    
    if not options['is_sufficient']:
        print_warning("Insufficient balance - rental cannot start")
        print_info(f"Suggested top-up: NPR {options['suggested_topup']:.2f}")
        return
    
    # Find available station
    station = Station.objects.filter(
        status='ONLINE',
        is_maintenance=False
    ).first()
    
    if not station:
        print_error("No available station found")
        return
    
    print_info(f"Using Station: {station.station_name} ({station.serial_number})")
    
    # Start rental
    try:
        service = RentalService()
        rental = service.start_rental(
            user=user,
            station_sn=station.serial_number,
            package_id=str(package.id)
        )
        
        print_success("Rental started successfully!")
        display_rental_info(rental)
        
        # Show updated balances
        print()
        user.refresh_from_db()
        display_user_balances(user)
        
    except Exception as e:
        print_error(f"Failed to start rental: {str(e)}")


def test_start_rental_postpaid(user_email, package_id=None):
    """Test starting a POSTPAID rental"""
    print_section("TEST: Start POSTPAID Rental")
    
    user = get_user(user_email)
    display_user_balances(user)
    
    # Get or find POSTPAID package
    if package_id:
        package = RentalPackage.objects.get(id=package_id)
    else:
        package = RentalPackage.objects.filter(
            payment_model='POSTPAID',
            is_active=True
        ).first()
        if not package:
            print_error("No POSTPAID package found")
            return
    
    print_info(f"Selected Package: {package.name} - NPR {package.price} ({package.duration_minutes} min)")
    print_warning("POSTPAID: Payment will be charged at return time based on usage")
    
    # Find available station
    station = Station.objects.filter(
        status='ONLINE',
        is_maintenance=False
    ).first()
    
    if not station:
        print_error("No available station found")
        return
    
    print_info(f"Using Station: {station.station_name} ({station.serial_number})")
    
    # Start rental
    try:
        service = RentalService()
        rental = service.start_rental(
            user=user,
            station_sn=station.serial_number,
            package_id=str(package.id)
        )
        
        print_success("Rental started successfully!")
        display_rental_info(rental)
        
        print_warning("Note: Payment status is PENDING - will be charged at return")
        
    except Exception as e:
        print_error(f"Failed to start rental: {str(e)}")


def test_extend_rental(rental_code, package_id=None):
    """Test extending an active rental"""
    print_section("TEST: Extend Rental")
    
    rental = get_rental(rental_code)
    
    if rental.status != 'ACTIVE':
        print_error(f"Rental is not ACTIVE (current status: {rental.status})")
        return
    
    display_rental_info(rental)
    display_user_balances(rental.user)
    
    # Get extension package
    if package_id:
        package = RentalPackage.objects.get(id=package_id)
    else:
        # Use same package type as original
        package = RentalPackage.objects.filter(
            payment_model='PREPAID',
            is_active=True,
            duration_minutes__lte=240  # Max 4 hours for extension
        ).first()
    
    if not package:
        print_error("No suitable package found for extension")
        return
    
    print_info(f"Extension Package: {package.name} - NPR {package.price} ({package.duration_minutes} min)")
    
    # Calculate payment options
    calc_service = PaymentCalculationService()
    options = calc_service.calculate_payment_options(
        user=rental.user,
        scenario='pre_payment',
        package_id=str(package.id)
    )
    
    print_info("Payment Calculation:")
    print_data("Extension Cost", f"NPR {options['total_amount']:.2f}")
    print_data("Points to Use", f"{options['payment_breakdown']['points_used']} (NPR {options['payment_breakdown']['points_amount']:.2f})")
    print_data("Wallet to Use", f"NPR {options['payment_breakdown']['wallet_used']:.2f}")
    print_data("Sufficient Funds", "YES ✅" if options['is_sufficient'] else f"NO ❌ (Shortfall: NPR {options['shortfall']:.2f})")
    
    if not options['is_sufficient']:
        print_warning("Insufficient balance - cannot extend rental")
        return
    
    # Extend rental
    try:
        service = RentalService()
        extension = service.extend_rental(
            rental_id=str(rental.id),
            user=rental.user,
            package_id=str(package.id)
        )
        
        print_success("Rental extended successfully!")
        
        rental.refresh_from_db()
        print_info("Updated Rental:")
        print_data("New Due Time", rental.due_at.strftime('%Y-%m-%d %H:%M:%S'))
        print_data("Total Amount Paid", f"NPR {rental.amount_paid:.2f}")
        print_data("Extended Minutes", extension.extended_minutes)
        
        rental.user.refresh_from_db()
        print()
        display_user_balances(rental.user)
        
    except Exception as e:
        print_error(f"Failed to extend rental: {str(e)}")


def test_pay_overdue(rental_code):
    """Test paying overdue rental dues"""
    print_section("TEST: Pay Overdue Rental")
    
    rental = get_rental(rental_code)
    
    if rental.payment_status == 'PAID':
        print_warning("Rental is already paid")
        return
    
    display_rental_info(rental)
    display_user_balances(rental.user)
    
    # Calculate total dues
    total_due = rental.amount_paid + rental.overdue_amount
    
    if total_due <= 0:
        print_warning("No outstanding dues")
        return
    
    print_warning(f"Total Outstanding: NPR {total_due:.2f}")
    
    # Calculate payment options
    calc_service = PaymentCalculationService()
    options = calc_service.calculate_payment_options(
        user=rental.user,
        scenario='post_payment',
        rental_id=str(rental.id)
    )
    
    print_info("Payment Calculation:")
    print_data("Total Due", f"NPR {options['total_amount']:.2f}")
    print_data("Points to Use", f"{options['payment_breakdown']['points_used']} (NPR {options['payment_breakdown']['points_amount']:.2f})")
    print_data("Wallet to Use", f"NPR {options['payment_breakdown']['wallet_used']:.2f}")
    print_data("Sufficient Funds", "YES ✅" if options['is_sufficient'] else f"NO ❌ (Shortfall: NPR {options['shortfall']:.2f})")
    
    if not options['is_sufficient']:
        print_warning("Insufficient balance - cannot pay dues")
        print_info(f"Suggested top-up: NPR {options['suggested_topup']:.2f}")
        return
    
    # Pay dues
    try:
        payment_service = RentalPaymentService()
        transaction = payment_service.pay_rental_due(
            user=rental.user,
            rental=rental,
            payment_breakdown=options['payment_breakdown']
        )
        
        print_success("Rental dues paid successfully!")
        
        rental.refresh_from_db()
        print_info("Updated Rental:")
        print_data("Payment Status", rental.payment_status)
        print_data("Overdue Amount", f"NPR {rental.overdue_amount:.2f}")
        print_data("Transaction ID", transaction.transaction_id)
        
        rental.user.refresh_from_db()
        print()
        display_user_balances(rental.user)
        
    except Exception as e:
        print_error(f"Failed to pay dues: {str(e)}")


def test_complete_flow(user_email):
    """Test complete rental flow: Start → Extend → Return → Pay"""
    print_section("TEST: Complete Rental Flow")
    
    user = get_user(user_email)
    
    # Step 1: Start PREPAID rental
    print(f"\n{Colors.BOLD}Step 1: Start PREPAID Rental{Colors.ENDC}")
    print("-" * 80)
    
    package = RentalPackage.objects.filter(
        payment_model='PREPAID',
        is_active=True,
        duration_minutes=60  # 1 hour
    ).first()
    
    if not package:
        print_error("No 1-hour PREPAID package found")
        return
    
    station = Station.objects.filter(
        status='ONLINE',
        is_maintenance=False
    ).first()
    
    if not station:
        print_error("No available station")
        return
    
    try:
        service = RentalService()
        rental = service.start_rental(
            user=user,
            station_sn=station.serial_number,
            package_id=str(package.id)
        )
        print_success(f"Rental started: {rental.rental_code}")
    except Exception as e:
        print_error(f"Failed: {str(e)}")
        return
    
    # Step 2: Extend rental
    print(f"\n{Colors.BOLD}Step 2: Extend Rental{Colors.ENDC}")
    print("-" * 80)
    
    extension_package = RentalPackage.objects.filter(
        payment_model='PREPAID',
        is_active=True,
        duration_minutes=60
    ).first()
    
    try:
        extension = service.extend_rental(
            rental_id=str(rental.id),
            user=user,
            package_id=str(extension_package.id)
        )
        print_success(f"Rental extended by {extension.extended_minutes} minutes")
    except Exception as e:
        print_warning(f"Extension failed: {str(e)}")
    
    # Step 3: Simulate late return
    print(f"\n{Colors.BOLD}Step 3: Simulate Late Return{Colors.ENDC}")
    print("-" * 80)
    
    # Make rental overdue (manually for testing)
    rental.due_at = timezone.now() - timedelta(hours=2)
    rental.save()
    print_info("Rental due time set to 2 hours ago")
    
    # Step 4: Return rental
    print(f"\n{Colors.BOLD}Step 4: Return Rental (with late fee){Colors.ENDC}")
    print("-" * 80)
    
    return_station = station
    return_slot = return_station.slots.filter(status='AVAILABLE').first()
    
    if not return_slot:
        print_warning("No available return slot - using same slot")
        return_slot = rental.slot
    
    try:
        rental = service.return_power_bank(
            rental_id=str(rental.id),
            return_station_sn=return_station.serial_number,
            return_slot_number=return_slot.slot_number
        )
        print_success("Rental returned")
        print_data("Status", rental.status)
        print_data("Payment Status", rental.payment_status)
        print_data("Late Fee", f"NPR {rental.overdue_amount:.2f}")
    except Exception as e:
        print_error(f"Return failed: {str(e)}")
        return
    
    # Step 5: Pay overdue (if needed)
    if rental.payment_status == 'PENDING':
        print(f"\n{Colors.BOLD}Step 5: Pay Outstanding Dues{Colors.ENDC}")
        print("-" * 80)
        
        total_due = rental.amount_paid + rental.overdue_amount
        print_warning(f"Outstanding: NPR {total_due:.2f}")
        
        calc_service = PaymentCalculationService()
        options = calc_service.calculate_payment_options(
            user=user,
            scenario='post_payment',
            rental_id=str(rental.id)
        )
        
        if options['is_sufficient']:
            try:
                payment_service = RentalPaymentService()
                payment_service.pay_rental_due(
                    user=user,
                    rental=rental,
                    payment_breakdown=options['payment_breakdown']
                )
                print_success("Dues paid successfully")
            except Exception as e:
                print_error(f"Payment failed: {str(e)}")
        else:
            print_warning(f"Insufficient balance (shortfall: NPR {options['shortfall']:.2f})")
    else:
        print_success("No outstanding dues")
    
    # Final summary
    print(f"\n{Colors.BOLD}Final Summary{Colors.ENDC}")
    print("-" * 80)
    rental.refresh_from_db()
    user.refresh_from_db()
    display_rental_info(rental)
    print()
    display_user_balances(user)


def main():
    parser = argparse.ArgumentParser(description='Test Rental Business Logic Flows')
    subparsers = parser.add_subparsers(dest='command', help='Test command')
    
    # Start rental commands
    start_prepaid = subparsers.add_parser('start-prepaid', help='Test PREPAID rental start')
    start_prepaid.add_argument('--email', required=True, help='User email')
    start_prepaid.add_argument('--package-id', help='Package UUID (optional)')
    
    start_postpaid = subparsers.add_parser('start-postpaid', help='Test POSTPAID rental start')
    start_postpaid.add_argument('--email', required=True, help='User email')
    start_postpaid.add_argument('--package-id', help='Package UUID (optional)')
    
    # Extend rental
    extend = subparsers.add_parser('extend', help='Test rental extension')
    extend.add_argument('--rental-code', required=True, help='Rental code')
    extend.add_argument('--package-id', help='Extension package UUID (optional)')
    
    # Pay overdue
    pay = subparsers.add_parser('pay-overdue', help='Test paying overdue dues')
    pay.add_argument('--rental-code', required=True, help='Rental code')
    
    # Complete flow
    complete = subparsers.add_parser('complete-flow', help='Test complete rental flow')
    complete.add_argument('--email', required=True, help='User email')
    
    args = parser.parse_args()
    
    if args.command == 'start-prepaid':
        test_start_rental_prepaid(args.email, args.package_id)
    elif args.command == 'start-postpaid':
        test_start_rental_postpaid(args.email, args.package_id)
    elif args.command == 'extend':
        test_extend_rental(args.rental_code, args.package_id)
    elif args.command == 'pay-overdue':
        test_pay_overdue(args.rental_code)
    elif args.command == 'complete-flow':
        test_complete_flow(args.email)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
