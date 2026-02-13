#!/usr/bin/env python3
"""
Automated test for all pay-due scenarios from DUE.md
Automatically sets balances and runs tests
"""

import requests
import json
import subprocess
import time
from decimal import Decimal

API_URL = "http://localhost:8010"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNTgxMTMyLCJpYXQiOjE3NzA5ODkxMzIsImp0aSI6IjllZjI3NmJiYWVmZDQ0YTY5N2MzYzNlYjY4ZGM5NWYzIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.vjOTD1H-MlFy9XlITFMIVdI_SVxdCEcdOq0AvCLV56w"

KHALTI_ID = "550e8400-e29b-41d4-a716-446655440301"
ESEWA_ID = "550e8400-e29b-41d4-a716-446655440302"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

results = []

def set_balance(wallet, points):
    """Set wallet and points balance."""
    cmd = f"""
docker exec cg-api-local python manage.py shell -c "
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.points.models import UserPoints
from decimal import Decimal

user = User.objects.get(id=1)
wallet, _ = Wallet.objects.get_or_create(user=user)
wallet.balance = Decimal('{wallet}')
wallet.save()

points, _ = UserPoints.objects.get_or_create(user=user)
points.current_points = {points}
points.save()
" 2>/dev/null
"""
    subprocess.run(cmd, shell=True, capture_output=True)
    time.sleep(0.5)  # Small delay

def cancel_rental(rental_id):
    """Cancel rental to reset for next test."""
    cmd = f"""
docker exec cg-api-local python manage.py shell -c "
from api.user.rentals.models import Rental
rental = Rental.objects.get(id='{rental_id}')
rental.status = 'CANCELLED'
rental.payment_status = 'PENDING'
rental.save()
" 2>/dev/null
"""
    subprocess.run(cmd, shell=True, capture_output=True)

def test_scenario(scenario_num, description, rental_id, wallet, points, payload, expected_status, expected_success):
    """Test a single scenario."""
    print(f"\n{'─'*70}")
    print(f"📋 Scenario {scenario_num}: {description}")
    print(f"   Setup: Wallet={wallet}, Points={points}")
    
    # Set balance
    set_balance(wallet, points)
    
    try:
        response = requests.post(
            f"{API_URL}/api/rentals/{rental_id}/pay-due",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        data = response.json()
        
        # Check results
        status_match = response.status_code == expected_status
        success_match = data.get("success") == expected_success
        
        # Print results
        status_icon = "✅" if status_match else "❌"
        success_icon = "✅" if success_match else "❌"
        
        print(f"   {status_icon} HTTP: {response.status_code} (expected {expected_status})")
        print(f"   {success_icon} success: {data.get('success')} (expected {expected_success})")
        
        # Additional checks
        if expected_status == 200 and expected_success:
            has_breakdown = "breakdown" in data.get("data", {})
            has_rental_status = "rental_status" in data.get("data", {})
            amount_is_string = isinstance(data.get("data", {}).get("amount_paid"), str)
            
            print(f"   {'✅' if has_breakdown else '❌'} Has breakdown")
            print(f"   {'✅' if has_rental_status else '❌'} Has rental_status")
            print(f"   {'✅' if amount_is_string else '❌'} amount_paid is string")
        
        elif expected_status == 402:
            has_error_code = data.get("error_code") == "payment_required"
            has_intent = "intent_id" in data.get("data", {})
            has_shortfall = "shortfall" in data.get("data", {})
            has_gateway = "gateway" in data.get("data", {})
            
            print(f"   {'✅' if has_error_code else '❌'} error_code: payment_required")
            print(f"   {'✅' if has_intent else '❌'} Has intent_id")
            print(f"   {'✅' if has_shortfall else '❌'} Has shortfall")
            print(f"   {'✅' if has_gateway else '❌'} Has gateway")
        
        passed = status_match and success_match
        results.append({
            "scenario": scenario_num,
            "description": description,
            "passed": passed
        })
        
        return passed
        
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        results.append({
            "scenario": scenario_num,
            "description": description,
            "passed": False,
            "error": str(e)
        })
        return False

def main():
    print("="*70)
    print("PAY DUE - AUTOMATED SCENARIO TESTING")
    print("="*70)
    print("Based on: plans/DUE.md")
    
    # Get rental ID
    rental_id = input("\nEnter rental ID with dues: ").strip()
    if not rental_id:
        print("❌ No rental ID provided")
        return
    
    print(f"\n🚀 Starting automated tests for rental: {rental_id}")
    print("   Tests will run automatically with balance changes")
    
    # Flush Redis
    print("\n🔧 Flushing Redis...")
    subprocess.run("docker exec cg-redis-local redis-cli FLUSHALL > /dev/null 2>&1", shell=True)
    
    # Run tests
    print("\n" + "="*70)
    print("RUNNING TESTS")
    print("="*70)
    
    # Scenario 1: wallet + SUFFICIENT
    test_scenario(1, "wallet + SUFFICIENT", rental_id, "200.00", 1000,
                  {"payment_mode": "wallet"}, 200, True)
    
    # Scenario 2: wallet + INSUFFICIENT
    test_scenario(2, "wallet + INSUFFICIENT", rental_id, "30.00", 1000,
                  {"payment_mode": "wallet", "payment_method_id": KHALTI_ID}, 402, False)
    
    # Scenario 3: points + SUFFICIENT
    test_scenario(3, "points + SUFFICIENT", rental_id, "200.00", 20000,
                  {"payment_mode": "points"}, 200, True)
    
    # Scenario 4: points + INSUFFICIENT
    test_scenario(4, "points + INSUFFICIENT", rental_id, "200.00", 2000,
                  {"payment_mode": "points", "payment_method_id": ESEWA_ID}, 402, False)
    
    # Scenario 5: wallet_points + SUFFICIENT
    test_scenario(5, "wallet_points + SUFFICIENT", rental_id, "60.00", 5000,
                  {"payment_mode": "wallet_points"}, 200, True)
    
    # Scenario 6: wallet_points + wallet short
    test_scenario(6, "wallet_points + wallet short", rental_id, "20.00", 5000,
                  {"payment_mode": "wallet_points", "payment_method_id": KHALTI_ID}, 402, False)
    
    # Scenario 7: wallet_points + points short
    test_scenario(7, "wallet_points + points short", rental_id, "60.00", 2000,
                  {"payment_mode": "wallet_points", "payment_method_id": ESEWA_ID}, 402, False)
    
    # Scenario 8: direct mode
    test_scenario(8, "direct mode", rental_id, "200.00", 10000,
                  {"payment_mode": "direct", "payment_method_id": KHALTI_ID}, 402, False)
    
    # Scenario 11: direct without payment_method_id
    test_scenario(11, "direct without payment_method_id", rental_id, "200.00", 10000,
                  {"payment_mode": "direct"}, 400, False)
    
    # Scenario 12: Insufficient without payment_method_id
    test_scenario(12, "Insufficient without payment_method_id", rental_id, "30.00", 1000,
                  {"payment_mode": "wallet"}, 400, False)
    
    # Scenario 13: Invalid payment_mode
    test_scenario(13, "Invalid payment_mode", rental_id, "200.00", 10000,
                  {"payment_mode": "invalid_mode"}, 400, False)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    print("\n" + "─"*70)
    for r in results:
        status = "✅" if r.get("passed") else "❌"
        print(f"{status} Scenario {r['scenario']}: {r['description']}")
    
    print("\n" + "="*70)
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    print("="*70)

if __name__ == "__main__":
    main()
