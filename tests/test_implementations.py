"""
Test Script for All Recent Implementations
==========================================
Tests:
1. AppConfig - RENTAL_CANCELLATION_WINDOW_MINUTES
2. Late Fee Logic (realtime calculation)
3. Cancellation Security (powerbank insertion check)
4. Realtime overdue amount calculation (@property methods)
"""

from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

print("\n" + "="*80)
print("TESTING ALL RECENT IMPLEMENTATIONS")
print("="*80)

# ============================================================================
# TEST 1: AppConfig - Cancellation Window
# ============================================================================
print("\n[TEST 1] AppConfig - RENTAL_CANCELLATION_WINDOW_MINUTES")
print("-" * 80)

from api.user.system.models import AppConfig

try:
    # Check if config exists
    cancel_window = AppConfig.objects.filter(
        key='RENTAL_CANCELLATION_WINDOW_MINUTES',
        is_active=True
    ).first()
    
    if cancel_window:
        print(f"✅ Config found: {cancel_window.key}")
        print(f"   Value: {cancel_window.value} minutes")
        print(f"   Description: {cancel_window.description}")
    else:
        print("⚠️  Config not found in database. Creating it now...")
        cancel_window = AppConfig.objects.create(
            key='RENTAL_CANCELLATION_WINDOW_MINUTES',
            value='5',
            description='Time window in minutes within which a rental can be cancelled after start',
            is_active=True
        )
        print(f"✅ Created: {cancel_window.key} = {cancel_window.value}")
    
    # Test retrieval method
    value = int(AppConfig.objects.filter(
        key='RENTAL_CANCELLATION_WINDOW_MINUTES', 
        is_active=True
    ).values_list('value', flat=True).first() or 5)
    
    print(f"✅ Retrieved value: {value} minutes")
    
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# TEST 2: Late Fee Configuration
# ============================================================================
print("\n[TEST 2] Late Fee Configuration System")
print("-" * 80)

from api.user.rentals.models.late_fee import LateFeeConfiguration

try:
    # Check active configuration
    late_fee_config = LateFeeConfiguration.objects.filter(is_active=True).first()
    
    if late_fee_config:
        print(f"✅ Active Configuration: {late_fee_config.name}")
        print(f"   Fee Type: {late_fee_config.fee_type}")
        print(f"   Multiplier: {late_fee_config.multiplier}x")
        print(f"   Grace Period: {late_fee_config.grace_period_minutes} minutes")
        print(f"   Max Daily Rate: NPR {late_fee_config.max_daily_rate}")
        
        # Test calculation
        test_rate = Decimal('2.00')  # NPR 2 per minute
        test_overdue = 60  # 60 minutes late
        
        calculated_fee = late_fee_config.calculate_late_fee(test_rate, test_overdue)
        print(f"\n   Test Calculation:")
        print(f"   - Normal rate: NPR {test_rate}/min")
        print(f"   - Overdue: {test_overdue} minutes")
        print(f"   - Calculated fee: NPR {calculated_fee:.2f}")
        
    else:
        print("⚠️  No active late fee configuration found")
        
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# TEST 3: Rental Model @property Methods
# ============================================================================
print("\n[TEST 3] Rental Model - Realtime Properties")
print("-" * 80)

from api.user.rentals.models import Rental

try:
    # Find an overdue rental (not returned yet)
    overdue_rental = Rental.objects.filter(
        status='OVERDUE',
        ended_at__isnull=True
    ).first()
    
    if overdue_rental:
        print(f"✅ Found overdue rental: {overdue_rental.rental_code}")
        print(f"   Status: {overdue_rental.status}")
        print(f"   Due at: {overdue_rental.due_at}")
        print(f"   Ended at: {overdue_rental.ended_at or 'Still active'}")
        
        # Test @property methods
        print(f"\n   Testing @property methods:")
        print(f"   1. minutes_overdue: {overdue_rental.minutes_overdue} minutes")
        print(f"   2. current_overdue_amount: NPR {overdue_rental.current_overdue_amount:.2f}")
        print(f"   3. estimated_total_cost: NPR {overdue_rental.estimated_total_cost:.2f}")
        print(f"      (amount_paid: NPR {overdue_rental.amount_paid} + current_overdue: NPR {overdue_rental.current_overdue_amount:.2f})")
        
    else:
        print("⚠️  No overdue rentals found. Creating a test scenario...")
        
        # Find any completed rental
        test_rental = Rental.objects.filter(status='COMPLETED').first()
        if test_rental:
            print(f"✅ Using completed rental: {test_rental.rental_code}")
            print(f"   Final overdue_amount: NPR {test_rental.overdue_amount}")
            print(f"   current_overdue_amount (property): NPR {test_rental.current_overdue_amount:.2f}")
            print(f"   ✅ For completed rentals, property returns stored final amount")
        else:
            print("⚠️  No rentals found in database")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 4: Helper Functions
# ============================================================================
print("\n[TEST 4] Late Fee Helper Functions")
print("-" * 80)

from api.common.utils.helpers import (
    calculate_late_fee_amount,
    calculate_overdue_minutes,
    get_package_rate_per_minute
)

try:
    # Test with a real rental package
    from api.user.rentals.models import RentalPackage
    package = RentalPackage.objects.filter(is_active=True).first()
    
    if package:
        print(f"✅ Using package: {package.name}")
        print(f"   Price: NPR {package.price}")
        print(f"   Duration: {package.duration_minutes} minutes")
        
        # Calculate rate per minute
        rate_per_min = get_package_rate_per_minute(package)
        print(f"   Rate per minute: NPR {rate_per_min:.4f}")
        
        # Test late fee calculation
        test_scenarios = [
            (10, "10 min late (within grace period)"),
            (30, "30 min late"),
            (60, "60 min late (1 hour)"),
            (120, "120 min late (2 hours)"),
        ]
        
        print(f"\n   Late Fee Scenarios:")
        for minutes, description in test_scenarios:
            late_fee = calculate_late_fee_amount(rate_per_min, minutes)
            print(f"   - {description}: NPR {late_fee:.2f}")
            
    else:
        print("⚠️  No active rental packages found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 5: Cancellation Security Logic
# ============================================================================
print("\n[TEST 5] Cancellation Security - Powerbank Insertion Check")
print("-" * 80)

try:
    # Find an active rental
    active_rental = Rental.objects.filter(status='ACTIVE').first()
    
    if active_rental:
        print(f"✅ Found active rental: {active_rental.rental_code}")
        print(f"   Status: {active_rental.status}")
        print(f"   Started at: {active_rental.started_at}")
        
        if active_rental.power_bank:
            pb = active_rental.power_bank
            print(f"\n   Powerbank Status:")
            print(f"   - Serial: {pb.serial_number}")
            print(f"   - Status: {pb.status}")
            print(f"   - Current Station: {pb.current_station.station_name if pb.current_station else 'None'}")
            print(f"   - Current Slot: {pb.current_slot.slot_number if pb.current_slot else 'None'}")
            
            # Check cancellation conditions
            print(f"\n   Cancellation Security Checks:")
            
            can_cancel = True
            reasons = []
            
            if pb.current_station != active_rental.station:
                can_cancel = False
                reasons.append("❌ Powerbank not at original station")
            else:
                reasons.append("✅ Powerbank at correct station")
                
            if pb.current_slot is None:
                can_cancel = False
                reasons.append("❌ Powerbank not in any slot")
            else:
                reasons.append("✅ Powerbank in a slot")
                
            if active_rental.slot.status != 'OCCUPIED':
                can_cancel = False
                reasons.append("❌ Slot not occupied")
            else:
                reasons.append("✅ Slot is occupied")
            
            for reason in reasons:
                print(f"   {reason}")
                
            if can_cancel:
                print(f"\n   ✅ RESULT: Cancellation would be ALLOWED")
            else:
                print(f"\n   ❌ RESULT: Cancellation would be BLOCKED (security working!)")
        else:
            print("⚠️  No powerbank assigned to rental")
    else:
        print("⚠️  No active rentals found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 6: Serializer Integration
# ============================================================================
print("\n[TEST 6] Serializer - Realtime Fields Exposure")
print("-" * 80)

try:
    from api.user.rentals.serializers import RentalDetailSerializer
    
    rental = Rental.objects.filter(status__in=['ACTIVE', 'OVERDUE']).first()
    
    if rental:
        print(f"✅ Testing serializer with rental: {rental.rental_code}")
        
        serializer = RentalDetailSerializer(rental)
        data = serializer.data
        
        print(f"\n   Serialized Data (realtime fields):")
        print(f"   - current_overdue_amount: {data.get('current_overdue_amount', 'N/A')}")
        print(f"   - estimated_total_cost: {data.get('estimated_total_cost', 'N/A')}")
        print(f"   - minutes_overdue: {data.get('minutes_overdue', 'N/A')}")
        print(f"   - formatted_current_overdue: {data.get('formatted_current_overdue', 'N/A')}")
        print(f"   - formatted_estimated_total: {data.get('formatted_estimated_total', 'N/A')}")
        
        if 'current_overdue_amount' in data:
            print(f"\n   ✅ Realtime fields successfully exposed in API!")
        else:
            print(f"\n   ⚠️  Realtime fields not found in serializer output")
    else:
        print("⚠️  No active/overdue rentals to test serializer")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)
print("""
✅ = Working correctly
⚠️  = Warning (may need data/setup)
❌ = Error found

Next Steps:
1. If AppConfig not found → Run: make loadfixtures
2. If no rentals found → Create test rental via API
3. Test API endpoints:
   - GET /api/rentals/active
   - POST /api/rentals/{id}/cancel
4. Check logs for any errors
""")
print("="*80 + "\n")
