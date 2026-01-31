#!/usr/bin/env python3
"""
Full Lifecycle Test for Franchise Partner Payout System
Tests complete flow: Revenue → Distribution → Vendor Payout → Franchise Payout
"""

import sys
import os
import django

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from api.partners.common.models import Partner, StationDistribution, RevenueDistribution, PayoutRequest
from api.user.rentals.models import Rental, RentalPackage
from api.user.payments.models import Transaction
from api.user.stations.models import StationSlot
import uuid

User = get_user_model()


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}\n")


def print_step(step_num, text):
    print(f"{Colors.BOLD}{Colors.CYAN}[STEP {step_num}] {text}{Colors.END}")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_db_state(franchise, vendor, step_name):
    """Print current database state"""
    print(f"\n{Colors.YELLOW}{'─'*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}DATABASE STATE: {step_name}{Colors.END}")
    print(f"{Colors.YELLOW}{'─'*80}{Colors.END}")
    
    print(f"\n{Colors.BOLD}Franchise (FR-001):{Colors.END}")
    print(f"  balance:        {franchise.balance} NPR")
    print(f"  total_earnings: {franchise.total_earnings} NPR")
    
    print(f"\n{Colors.BOLD}Vendor (VN-003):{Colors.END}")
    print(f"  balance:        {vendor.balance} NPR")
    print(f"  total_earnings: {vendor.total_earnings} NPR")
    
    # Show revenue distributions
    revenues = RevenueDistribution.objects.filter(franchise=franchise)
    print(f"\n{Colors.BOLD}Revenue Distributions:{Colors.END}")
    print(f"  Total: {revenues.count()}")
    print(f"  Distributed: {revenues.filter(is_distributed=True).count()}")
    print(f"  Pending: {revenues.filter(is_distributed=False).count()}")
    
    # Show payouts
    franchise_payouts = PayoutRequest.objects.filter(
        partner=franchise,
        payout_type='CHARGEGHAR_TO_FRANCHISE'
    )
    vendor_payouts = PayoutRequest.objects.filter(
        partner=vendor,
        payout_type='FRANCHISE_TO_VENDOR'
    )
    
    print(f"\n{Colors.BOLD}Franchise Payouts:{Colors.END}")
    for status in ['PENDING', 'APPROVED', 'PROCESSING', 'COMPLETED', 'REJECTED']:
        count = franchise_payouts.filter(status=status).count()
        if count > 0:
            print(f"  {status}: {count}")
    
    print(f"\n{Colors.BOLD}Vendor Payouts:{Colors.END}")
    for status in ['PENDING', 'APPROVED', 'COMPLETED', 'REJECTED']:
        count = vendor_payouts.filter(status=status).count()
        if count > 0:
            print(f"  {status}: {count}")
    
    print(f"{Colors.YELLOW}{'─'*80}{Colors.END}\n")


def cleanup():
    """Clean slate - reset all data"""
    print_step(0, "CLEANUP - Reset to Clean Slate")
    
    franchise = Partner.objects.get(code='FR-001')
    vendor = Partner.objects.get(code='VN-003')
    
    # Delete revenue distributions
    deleted = RevenueDistribution.objects.filter(franchise=franchise).delete()
    print_info(f"Deleted {deleted[0]} revenue distributions")
    
    # Reject pending payouts
    rejected = PayoutRequest.objects.filter(
        status__in=['PENDING', 'APPROVED', 'PROCESSING']
    ).update(status='REJECTED', rejection_reason='Test cleanup')
    print_info(f"Rejected {rejected} pending payouts")
    
    # Reset balances
    franchise.balance = 0
    franchise.total_earnings = 0
    franchise.save()
    
    vendor.balance = 0
    vendor.total_earnings = 0
    vendor.save()
    
    print_success("Clean slate ready")
    print_db_state(franchise, vendor, "After Cleanup")
    
    return franchise, vendor


def create_revenue_transactions(franchise, vendor):
    """Create 3 revenue transactions"""
    print_step(1, "CREATE REVENUE TRANSACTIONS")
    
    vendor_station = StationDistribution.objects.filter(partner=vendor, is_active=True).first().station
    slot = StationSlot.objects.filter(station=vendor_station).first()
    package = RentalPackage.objects.filter(is_active=True).first()
    test_user = User.objects.filter(is_superuser=False).first()
    
    now = timezone.now()
    
    transactions = [
        (Decimal('100.00'), Decimal('13.00'), Decimal('5.00'), Decimal('82.00'), 
         Decimal('41.00'), Decimal('34.85'), Decimal('6.15')),
        (Decimal('150.00'), Decimal('19.50'), Decimal('7.50'), Decimal('123.00'), 
         Decimal('61.50'), Decimal('52.28'), Decimal('9.23')),
        (Decimal('200.00'), Decimal('26.00'), Decimal('10.00'), Decimal('164.00'), 
         Decimal('82.00'), Decimal('69.70'), Decimal('12.30')),
    ]
    
    total_franchise = Decimal('0')
    total_vendor = Decimal('0')
    
    for i, (gross, vat, service, net, cg, fr, vn) in enumerate(transactions, 1):
        rental = Rental.objects.create(
            user=test_user, station=vendor_station, return_station=vendor_station,
            slot=slot, package=package, power_bank=None,
            rental_code=f'TEST{uuid.uuid4().hex[:6].upper()}', status='COMPLETED', payment_status='PAID',
            started_at=now - timedelta(hours=2), ended_at=now,
            due_at=now, amount_paid=gross, overdue_amount=Decimal('0.00'),
            is_returned_on_time=True, timely_return_bonus_awarded=False,
            rental_metadata={}, created_at=now
        )
        
        txn = Transaction.objects.create(
            user=test_user, related_rental=rental,
            transaction_id=f'TEST{uuid.uuid4().hex[:10].upper()}',
            transaction_type='RENTAL_PAYMENT', amount=gross, currency='NPR',
            status='COMPLETED', payment_method_type='KHALTI',
            gateway_reference=f'KHALTI{uuid.uuid4().hex[:8].upper()}',
            gateway_response={}, created_at=now
        )
        
        RevenueDistribution.objects.create(
            transaction=txn, rental=rental, station=vendor_station,
            franchise=franchise, vendor=vendor,
            gross_amount=gross, vat_amount=vat, service_charge=service, net_amount=net,
            chargeghar_share=cg, franchise_share=fr, vendor_share=vn,
            is_distributed=False, distributed_at=None,
            calculation_details={}, is_reversal=False, reversal_reason='',
            created_at=now
        )
        
        total_franchise += fr
        total_vendor += vn
        print_info(f"Transaction {i}: {gross} NPR → Franchise: {fr}, Vendor: {vn}")
    
    print_success(f"Created 3 transactions")
    print_info(f"Total franchise share: {total_franchise} NPR")
    print_info(f"Total vendor share: {total_vendor} NPR")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Revenue Creation")


def distribute_revenue(franchise, vendor):
    """Distribute revenue to partners"""
    print_step(2, "DISTRIBUTE REVENUE")
    
    revenues = RevenueDistribution.objects.filter(franchise=franchise, is_distributed=False)
    count = revenues.count()
    
    for rev in revenues:
        franchise.balance += rev.franchise_share
        franchise.total_earnings += rev.franchise_share
        vendor.balance += rev.vendor_share
        vendor.total_earnings += rev.vendor_share
        rev.is_distributed = True
        rev.save()
    
    franchise.save()
    vendor.save()
    
    print_success(f"Distributed {count} transactions")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Revenue Distribution")


def test_vendor_payout(franchise, vendor):
    """Test vendor payout flow"""
    print_step(3, "VENDOR PAYOUT FLOW")
    
    from api.partners.common.repositories import PayoutRequestRepository
    
    # Create payout request
    print_info("Creating vendor payout request (20 NPR)...")
    payout = PayoutRequestRepository.create(
        partner_id=str(vendor.id),
        amount=20,
        bank_name='Vendor Bank',
        account_number='1234567890',
        account_holder_name='Vendor Test'
    )
    print_success(f"Created: {payout.reference_id} (Status: {payout.status})")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Vendor Payout Request")
    
    # Approve
    print_info("Franchise approving payout...")
    from api.partners.franchise.services import FranchiseRevenuePayoutService
    service = FranchiseRevenuePayoutService()
    payout = service.approve_vendor_payout(franchise, str(payout.id))
    print_success(f"Approved: {payout.status}")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Vendor Payout Approval")
    
    # Complete
    print_info("Franchise completing payout...")
    payout = service.complete_vendor_payout(franchise, str(payout.id))
    print_success(f"Completed: {payout.status}")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Vendor Payout Completion")
    
    return payout


def test_franchise_payout(franchise, vendor):
    """Test franchise payout flow"""
    print_step(4, "FRANCHISE PAYOUT FLOW")
    
    from api.partners.franchise.services import FranchiseRevenuePayoutService
    
    # Create payout request
    print_info("Franchise requesting payout (50 NPR)...")
    service = FranchiseRevenuePayoutService()
    payout = service.request_payout(
        franchise=franchise,
        amount=50,
        bank_name='Franchise Bank',
        account_number='9876543210',
        account_holder_name='Pro Boy'
    )
    print_success(f"Created: {payout.reference_id} (Status: {payout.status})")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Franchise Payout Request")
    
    # Admin approve
    print_info("Admin approving payout...")
    from api.admin.services.admin_partner_service import AdminPartnerService
    admin_user = User.objects.filter(is_superuser=True).first()
    admin_service = AdminPartnerService()
    payout = admin_service.approve_payout(str(payout.id), admin_user)
    print_success(f"Approved: {payout.status}")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Admin Approval")
    
    # Admin process
    print_info("Admin processing payout...")
    payout = admin_service.process_payout(str(payout.id), admin_user)
    print_success(f"Processing: {payout.status}")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Admin Processing")
    
    # Admin complete
    print_info("Admin completing payout...")
    payout = admin_service.complete_payout(str(payout.id), admin_user)
    print_success(f"Completed: {payout.status}")
    
    franchise.refresh_from_db()
    vendor.refresh_from_db()
    print_db_state(franchise, vendor, "After Admin Completion")
    
    return payout


def verify_final_state(franchise, vendor):
    """Verify final state matches expectations"""
    print_step(5, "VERIFY FINAL STATE")
    
    expected_franchise_balance = Decimal('86.83')
    expected_franchise_earnings = Decimal('156.83')
    expected_vendor_balance = Decimal('7.68')
    expected_vendor_earnings = Decimal('27.68')
    
    errors = []
    
    if franchise.balance != expected_franchise_balance:
        errors.append(f"Franchise balance: expected {expected_franchise_balance}, got {franchise.balance}")
    else:
        print_success(f"Franchise balance: {franchise.balance} NPR")
    
    if franchise.total_earnings != expected_franchise_earnings:
        errors.append(f"Franchise earnings: expected {expected_franchise_earnings}, got {franchise.total_earnings}")
    else:
        print_success(f"Franchise total_earnings: {franchise.total_earnings} NPR")
    
    if vendor.balance != expected_vendor_balance:
        errors.append(f"Vendor balance: expected {expected_vendor_balance}, got {vendor.balance}")
    else:
        print_success(f"Vendor balance: {vendor.balance} NPR")
    
    if vendor.total_earnings != expected_vendor_earnings:
        errors.append(f"Vendor earnings: expected {expected_vendor_earnings}, got {vendor.total_earnings}")
    else:
        print_success(f"Vendor total_earnings: {vendor.total_earnings} NPR")
    
    if errors:
        print_error("VERIFICATION FAILED:")
        for error in errors:
            print_error(f"  {error}")
        return False
    
    print_success("ALL VERIFICATIONS PASSED!")
    return True


def main():
    print_header("FRANCHISE PARTNER PAYOUT - FULL LIFECYCLE TEST")
    
    try:
        # Cleanup
        franchise, vendor = cleanup()
        
        # Step 1: Create revenue
        create_revenue_transactions(franchise, vendor)
        
        # Step 2: Distribute revenue
        distribute_revenue(franchise, vendor)
        
        # Step 3: Vendor payout
        test_vendor_payout(franchise, vendor)
        
        # Step 4: Franchise payout
        test_franchise_payout(franchise, vendor)
        
        # Step 5: Verify
        success = verify_final_state(franchise, vendor)
        
        if success:
            print_header("✅ ALL TESTS PASSED - PRODUCTION READY ✅")
            return 0
        else:
            print_header("❌ TESTS FAILED - REVIEW ERRORS ABOVE ❌")
            return 1
            
    except Exception as e:
        print_error(f"TEST FAILED WITH EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
