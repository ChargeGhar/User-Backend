"""
Comprehensive Rental Start Testing Framework
Tests all 24 scenarios from plans/Rental.md
"""
import subprocess
import json
import requests
from decimal import Decimal
from typing import Dict, Optional

API_URL = "http://localhost:8010"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNTgxMTMyLCJpYXQiOjE3NzA5ODkxMzIsImp0aSI6IjllZjI3NmJiYWVmZDQ0YTY5N2MzYzNlYjY4ZGM5NWYzIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.vjOTD1H-MlFy9XlITFMIVdI_SVxdCEcdOq0AvCLV56w"

class TestFramework:
    def __init__(self):
        self.test_data = {}
        self.results = []
        
    def run_django(self, code: str) -> str:
        """Execute Django shell command"""
        cmd = f'docker exec cg-api-local python manage.py shell -c "{code}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    
    def setup_test_data(self):
        """Get all test data from database"""
        print("📋 Fetching test data...")
        
        code = """
from api.user.rentals.models import RentalPackage
from api.user.stations.models import Station, PowerBank, StationSlot
from api.user.payments.models import PaymentMethod

# Packages
prepaid = RentalPackage.objects.filter(is_active=True, payment_model='PREPAID').first()
postpaid = RentalPackage.objects.filter(is_active=True, payment_model='POSTPAID').first()

if prepaid:
    print(f'PREPAID_ID:{prepaid.id}')
    print(f'PREPAID_PRICE:{prepaid.price}')

if postpaid:
    print(f'POSTPAID_ID:{postpaid.id}')
    print(f'POSTPAID_PRICE:{postpaid.price}')

# Station with power banks
station = Station.objects.filter(status='ONLINE', is_maintenance=False).first()
if station:
    print(f'STATION_SN:{station.serial_number}')
    print(f'STATION_ID:{station.id}')
    
    # Check power banks
    pb_count = PowerBank.objects.filter(
        current_station=station,
        status='AVAILABLE',
        battery_level__gte=20
    ).count()
    print(f'POWERBANKS:{pb_count}')

# Payment method
pm = PaymentMethod.objects.filter(is_active=True).first()
if pm:
    print(f'PAYMENT_METHOD_ID:{pm.id}')
"""
        output = self.run_django(code)
        
        for line in output.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                self.test_data[key] = value.strip()
        
        print(f"✓ PREPAID: {self.test_data.get('PREPAID_ID')} - NPR {self.test_data.get('PREPAID_PRICE')}")
        print(f"✓ POSTPAID: {self.test_data.get('POSTPAID_ID')} - NPR {self.test_data.get('POSTPAID_PRICE')}")
        print(f"✓ Station: {self.test_data.get('STATION_SN')}")
        print(f"✓ Power Banks: {self.test_data.get('POWERBANKS', '0')}")
        print(f"✓ Payment Method: {self.test_data.get('PAYMENT_METHOD_ID')}")
        
        return int(self.test_data.get('POWERBANKS', '0')) > 0
    
    def create_power_banks(self):
        """Create test power banks at station"""
        print("\n🔧 Creating test power banks...")
        
        station_id = self.test_data.get('STATION_ID')
        if not station_id:
            print("❌ No station found")
            return False
        
        code = f"""
from api.user.stations.models import Station, PowerBank, StationSlot
from decimal import Decimal

station = Station.objects.get(id='{station_id}')

# Create 3 power banks
for i in range(1, 4):
    # Create slot
    slot, _ = StationSlot.objects.get_or_create(
        station=station,
        slot_number=i,
        defaults={{'status': 'AVAILABLE'}}
    )
    
    # Create power bank
    pb, created = PowerBank.objects.get_or_create(
        serial_number=f'TEST-PB-{{i:03d}}',
        defaults={{
            'current_station': station,
            'current_slot': slot,
            'status': 'AVAILABLE',
            'battery_level': 95,
            'health_status': 'GOOD'
        }}
    )
    
    if created:
        print(f'Created: {{pb.serial_number}}')
    else:
        pb.current_station = station
        pb.current_slot = slot
        pb.status = 'AVAILABLE'
        pb.battery_level = 95
        pb.save()
        print(f'Updated: {{pb.serial_number}}')

print('✅ Power banks ready')
"""
        output = self.run_django(code)
        print(output)
        return True
    
    def set_balance(self, wallet: str, points: int):
        """Set user wallet and points balance"""
        code = f"""
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from decimal import Decimal

user = User.objects.get(id=1)

wallet, _ = Wallet.objects.get_or_create(user=user)
wallet.balance = Decimal('{wallet}')
wallet.save()

points_obj, _ = UserPoints.objects.get_or_create(user=user)
points_obj.current_points = {points}
points_obj.save()

print('OK')
"""
        self.run_django(code)
    
    def get_balance(self) -> tuple:
        """Get current balance"""
        code = """
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints

user = User.objects.get(id=1)
wallet = Wallet.objects.filter(user=user).first()
points = UserPoints.objects.filter(user=user).first()

print(f'{wallet.balance if wallet else 0}|{points.current_points if points else 0}')
"""
        output = self.run_django(code)
        for line in output.split('\n'):
            if '|' in line:
                w, p = line.split('|')
                return Decimal(w), int(p)
        return Decimal('0'), 0
    
    def cancel_active_rentals(self):
        """Cancel any active rentals"""
        code = """
from api.user.rentals.models import Rental
from api.user.auth.models import User

user = User.objects.get(id=1)
active = Rental.objects.filter(
    user=user,
    status__in=['PENDING', 'PENDING_POPUP', 'ACTIVE', 'OVERDUE']
)
for rental in active:
    rental.status = 'CANCELLED'
    rental.save()
"""
        self.run_django(code)
    
    def test_scenario(self, num: int, name: str, setup: Dict, request: Dict, 
                     expected_status: int, expected_success: bool):
        """Test a single scenario"""
        print(f"\n{'='*70}")
        print(f"Scenario {num}: {name}")
        print(f"{'='*70}")
        
        # Cancel any active rentals first
        self.cancel_active_rentals()
        
        # Setup
        if 'wallet' in setup or 'points' in setup:
            wallet = setup.get('wallet', '0')
            points = setup.get('points', 0)
            print(f"Setup: Wallet=NPR {wallet}, Points={points}")
            self.set_balance(wallet, points)
        
        # Get balance before
        wallet_before, points_before = self.get_balance()
        print(f"Before: Wallet=NPR {wallet_before}, Points={points_before}")
        
        # Make request
        print(f"\nRequest: {json.dumps(request, indent=2)}")
        
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{API_URL}/api/rentals/start",
            headers=headers,
            json=request
        )
        
        print(f"\nHTTP: {response.status_code} (Expected: {expected_status})")
        
        try:
            result = response.json()
            success = result.get('success')
            print(f"Success: {success} (Expected: {expected_success})")
            
            # Show key response fields
            if success:
                data = result.get('data', {})
                print(f"Rental: {data.get('rental_code', 'N/A')}")
                print(f"Status: {data.get('status', 'N/A')}")
            else:
                error_code = result.get('error_code') or result.get('error', {}).get('code')
                print(f"Error: {error_code}")
                if error_code == 'payment_required':
                    data = result.get('data', {})
                    print(f"Shortfall: NPR {data.get('shortfall', 'N/A')}")
            
            # Get balance after
            wallet_after, points_after = self.get_balance()
            print(f"\nAfter: Wallet=NPR {wallet_after}, Points={points_after}")
            print(f"Change: Wallet={wallet_after - wallet_before}, Points={points_after - points_before}")
            
            # Verify
            passed = (response.status_code == expected_status and success == expected_success)
            
            if passed:
                print("\n✅ PASS")
            else:
                print("\n❌ FAIL")
                print(f"Full response: {json.dumps(result, indent=2)[:500]}")
            
            self.results.append({
                'scenario': num,
                'name': name,
                'passed': passed,
                'status': response.status_code,
                'success': success
            })
            
            return passed
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print(f"Response: {response.text[:500]}")
            self.results.append({
                'scenario': num,
                'name': name,
                'passed': False,
                'error': str(e)
            })
            return False
    
    def run_all_tests(self):
        """Run all 24 scenarios"""
        station_sn = self.test_data['STATION_SN']
        prepaid_id = self.test_data['PREPAID_ID']
        postpaid_id = self.test_data.get('POSTPAID_ID')
        pm_id = self.test_data.get('PAYMENT_METHOD_ID')
        
        print("\n" + "="*70)
        print("RUNNING ALL SCENARIOS")
        print("="*70)
        
        # PREPAID Scenarios
        self.test_scenario(
            1, "PREPAID + wallet + SUFFICIENT",
            {'wallet': '100.00', 'points': 0},
            {'station_sn': station_sn, 'package_id': prepaid_id, 'payment_mode': 'wallet'},
            201, True
        )
        
        self.test_scenario(
            2, "PREPAID + wallet + INSUFFICIENT",
            {'wallet': '20.00', 'points': 0},
            {'station_sn': station_sn, 'package_id': prepaid_id, 'payment_mode': 'wallet', 
             'payment_method_id': pm_id},
            402, False
        )
        
        self.test_scenario(
            3, "PREPAID + points + SUFFICIENT",
            {'wallet': '0', 'points': 500},
            {'station_sn': station_sn, 'package_id': prepaid_id, 'payment_mode': 'points'},
            201, True
        )
        
        self.test_scenario(
            4, "PREPAID + points + INSUFFICIENT",
            {'wallet': '0', 'points': 100},
            {'station_sn': station_sn, 'package_id': prepaid_id, 'payment_mode': 'points',
             'payment_method_id': pm_id},
            402, False
        )
        
        self.test_scenario(
            5, "PREPAID + wallet_points + SUFFICIENT",
            {'wallet': '30.00', 'points': 200},
            {'station_sn': station_sn, 'package_id': prepaid_id, 'payment_mode': 'wallet_points',
             'wallet_amount': '30.00', 'points_to_use': 200},
            201, True
        )
        
        self.test_scenario(
            6, "PREPAID + wallet_points + INSUFFICIENT (wallet short)",
            {'wallet': '15.00', 'points': 200},
            {'station_sn': station_sn, 'package_id': prepaid_id, 'payment_mode': 'wallet_points',
             'wallet_amount': '30.00', 'points_to_use': 200, 'payment_method_id': pm_id},
            402, False
        )
        
        self.test_scenario(
            7, "PREPAID + wallet_points + INSUFFICIENT (points short)",
            {'wallet': '30.00', 'points': 50},
            {'station_sn': station_sn, 'package_id': prepaid_id, 'payment_mode': 'wallet_points',
             'wallet_amount': '30.00', 'points_to_use': 200, 'payment_method_id': pm_id},
            402, False
        )
        
        self.test_scenario(
            8, "PREPAID + direct",
            {'wallet': '100.00', 'points': 0},
            {'station_sn': station_sn, 'package_id': prepaid_id, 'payment_mode': 'direct',
             'payment_method_id': pm_id},
            402, False
        )
        
        # POSTPAID Scenarios
        if postpaid_id:
            self.test_scenario(
                9, "POSTPAID + wallet + SUFFICIENT",
                {'wallet': '100.00', 'points': 0},
                {'station_sn': station_sn, 'package_id': postpaid_id, 'payment_mode': 'wallet'},
                201, True
            )
            
            self.test_scenario(
                10, "POSTPAID + wallet + INSUFFICIENT",
                {'wallet': '20.00', 'points': 0},
                {'station_sn': station_sn, 'package_id': postpaid_id, 'payment_mode': 'wallet',
                 'payment_method_id': pm_id},
                402, False
            )
            
            self.test_scenario(
                11, "POSTPAID + points (NOT SUPPORTED)",
                {'wallet': '100.00', 'points': 500},
                {'station_sn': station_sn, 'package_id': postpaid_id, 'payment_mode': 'points'},
                400, False
            )
            
            self.test_scenario(
                12, "POSTPAID + wallet_points (NOT SUPPORTED)",
                {'wallet': '100.00', 'points': 500},
                {'station_sn': station_sn, 'package_id': postpaid_id, 'payment_mode': 'wallet_points',
                 'wallet_amount': '50.00', 'points_to_use': 300},
                400, False
            )
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)
        
        print(f"\nTotal: {total} scenarios")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {total - passed} ❌")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        # Show failures
        failures = [r for r in self.results if not r['passed']]
        if failures:
            print(f"\n❌ Failed Scenarios:")
            for f in failures:
                print(f"  - Scenario {f['scenario']}: {f['name']}")
        
        return passed == total

def main():
    print("="*70)
    print("COMPREHENSIVE RENTAL START TESTING")
    print("="*70)
    
    framework = TestFramework()
    
    # Setup
    has_powerbanks = framework.setup_test_data()
    
    if not has_powerbanks:
        print("\n⚠️  No power banks found. Creating...")
        framework.create_power_banks()
        framework.setup_test_data()
    
    # Run tests
    success = framework.run_all_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
