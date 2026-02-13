"""
Test Failed Scenarios - Focused Testing
"""
import subprocess
import json
import requests
from decimal import Decimal

API_URL = "http://localhost:8010"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNTgxMTMyLCJpYXQiOjE3NzA5ODkxMzIsImp0aSI6IjllZjI3NmJiYWVmZDQ0YTY5N2MzYzNlYjY4ZGM5NWYzIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.vjOTD1H-MlFy9XlITFMIVdI_SVxdCEcdOq0AvCLV56w"

def run_django(code):
    cmd = f'docker exec cg-api-local python manage.py shell -c "{code}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def cancel_active_rentals():
    """Cancel any active rentals"""
    code = """
from api.user.rentals.models import Rental
from api.user.auth.models import User

user = User.objects.get(id=1)
active = Rental.objects.filter(
    user=user,
    status__in=['PENDING', 'PENDING_POPUP', 'ACTIVE', 'OVERDUE']
)
count = active.count()
for rental in active:
    rental.status = 'CANCELLED'
    rental.save()
print(f'Cancelled: {count}')
"""
    output = run_django(code)
    print(f"  {output}")

def set_balance(wallet, points):
    code = f"""
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from decimal import Decimal

user = User.objects.get(id=1)
wallet_obj, _ = Wallet.objects.get_or_create(user=user)
wallet_obj.balance = Decimal('{wallet}')
wallet_obj.save()

points_obj, _ = UserPoints.objects.get_or_create(user=user)
points_obj.current_points = {points}
points_obj.save()
print('OK')
"""
    run_django(code)

def test_scenario(name, setup, request_data, expected_status):
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"{'='*70}")
    
    # Cancel active rentals
    print("Cleanup:")
    cancel_active_rentals()
    
    # Setup balance
    if setup:
        wallet = setup.get('wallet', '0')
        points = setup.get('points', 0)
        print(f"Setup: Wallet=NPR {wallet}, Points={points}")
        set_balance(wallet, points)
    
    # Make request
    print(f"\nRequest: {json.dumps(request_data, indent=2)}")
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_URL}/api/rentals/start",
        headers=headers,
        json=request_data
    )
    
    print(f"\nResponse:")
    print(f"HTTP Status: {response.status_code} (Expected: {expected_status})")
    
    try:
        result = response.json()
        print(f"Success: {result.get('success')}")
        
        if result.get('success'):
            data = result.get('data', {})
            print(f"✅ Rental Code: {data.get('rental_code')}")
            print(f"✅ Status: {data.get('status')}")
            print(f"✅ Payment Status: {data.get('payment', {}).get('payment_status')}")
            
            # Show pricing
            pricing = data.get('pricing', {})
            print(f"✅ Amount Paid: NPR {pricing.get('amount_paid')}")
            
            # Show payment breakdown
            payment = data.get('payment', {})
            breakdown = payment.get('breakdown', {})
            if breakdown:
                print(f"✅ Breakdown: Wallet={breakdown.get('wallet_amount')}, Points={breakdown.get('points_used')}")
        else:
            error_code = result.get('error_code') or result.get('error', {}).get('code')
            message = result.get('message') or result.get('error', {}).get('message')
            print(f"❌ Error: {error_code}")
            print(f"❌ Message: {message}")
        
        # Verify
        if response.status_code == expected_status:
            print(f"\n✅ PASS")
            return True
        else:
            print(f"\n❌ FAIL - Status mismatch")
            print(f"Full response: {json.dumps(result, indent=2)[:800]}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"Raw: {response.text[:500]}")
        return False

def main():
    print("="*70)
    print("TESTING FAILED SCENARIOS")
    print("="*70)
    
    # Get test data
    code = """
from api.user.rentals.models import RentalPackage
from api.user.stations.models import Station
from api.user.payments.models import PaymentMethod

prepaid = RentalPackage.objects.filter(is_active=True, payment_model='PREPAID').first()
postpaid = RentalPackage.objects.filter(is_active=True, payment_model='POSTPAID').first()
station = Station.objects.filter(status='ONLINE').first()
pm = PaymentMethod.objects.filter(is_active=True).first()

print(f'{prepaid.id}|{prepaid.price}|{postpaid.id if postpaid else ""}|{station.serial_number}|{pm.id if pm else ""}')
"""
    output = run_django(code)
    
    prepaid_id = None
    prepaid_price = None
    postpaid_id = None
    station_sn = None
    pm_id = None
    
    for line in output.split('\n'):
        if '|' in line and not line.startswith('82 objects'):
            parts = line.split('|')
            if len(parts) >= 5:
                prepaid_id = parts[0]
                prepaid_price = parts[1]
                postpaid_id = parts[2] if parts[2] else None
                station_sn = parts[3]
                pm_id = parts[4] if parts[4] else None
                break
    
    print(f"\n✓ PREPAID: {prepaid_id} - NPR {prepaid_price}")
    print(f"✓ POSTPAID: {postpaid_id}")
    print(f"✓ Station: {station_sn}")
    print(f"✓ Payment Method: {pm_id}")
    
    results = []
    
    # Test the 3 failed scenarios
    
    # Scenario 3: PREPAID + points + SUFFICIENT
    results.append(test_scenario(
        "Scenario 3: PREPAID + points + SUFFICIENT",
        {'wallet': '0', 'points': 500},
        {
            'station_sn': station_sn,
            'package_id': prepaid_id,
            'payment_mode': 'points'
        },
        201
    ))
    
    # Scenario 5: PREPAID + wallet_points + SUFFICIENT
    results.append(test_scenario(
        "Scenario 5: PREPAID + wallet_points + SUFFICIENT",
        {'wallet': '30.00', 'points': 200},
        {
            'station_sn': station_sn,
            'package_id': prepaid_id,
            'payment_mode': 'wallet_points',
            'wallet_amount': '30.00',
            'points_to_use': 200
        },
        201
    ))
    
    # Scenario 9: POSTPAID + wallet + SUFFICIENT
    if postpaid_id:
        results.append(test_scenario(
            "Scenario 9: POSTPAID + wallet + SUFFICIENT",
            {'wallet': '100.00', 'points': 0},
            {
                'station_sn': station_sn,
                'package_id': postpaid_id,
                'payment_mode': 'wallet'
            },
            201
        ))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL SCENARIOS FIXED!")
    else:
        print("\n⚠️  Some scenarios still failing")
    
    return passed == total

if __name__ == "__main__":
    exit(0 if main() else 1)
