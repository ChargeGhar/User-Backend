#!/usr/bin/env python3
"""
Comprehensive test for all pay-due scenarios from DUE.md
"""

import requests
import json
from decimal import Decimal

API_URL = "http://localhost:8010"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNTgxMTMyLCJpYXQiOjE3NzA5ODkxMzIsImp0aSI6IjllZjI3NmJiYWVmZDQ0YTY5N2MzYzNlYjY4ZGM5NWYzIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.vjOTD1H-MlFy9XlITFMIVdI_SVxdCEcdOq0AvCLV56w"

KHALTI_ID = "550e8400-e29b-41d4-a716-446655440301"
ESEWA_ID = "550e8400-e29b-41d4-a716-446655440302"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Test results
results = []

def print_header(title):
    print(f"\n{'='*70}")
    print(f"{title}")
    print('='*70)

def test_scenario(scenario_num, description, rental_id, payload, expected_status, expected_success):
    """Test a single scenario."""
    print(f"\n📋 Scenario {scenario_num}: {description}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_URL}/api/rentals/{rental_id}/pay-due",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        data = response.json()
        
        # Check HTTP status
        status_match = response.status_code == expected_status
        success_match = data.get("success") == expected_success
        
        # Print results
        print(f"   HTTP Status: {response.status_code} {'✅' if status_match else '❌ Expected ' + str(expected_status)}")
        print(f"   success: {data.get('success')} {'✅' if success_match else '❌ Expected ' + str(expected_success)}")
        
        # Additional checks based on response type
        if expected_status == 200 and expected_success:
            # Success response checks
            checks = {
                "transaction_id": "transaction_id" in data.get("data", {}),
                "breakdown": "breakdown" in data.get("data", {}),
                "rental_status": "rental_status" in data.get("data", {}),
                "amount_paid is string": isinstance(data.get("data", {}).get("amount_paid"), str),
            }
            for check, passed in checks.items():
                print(f"   {check}: {'✅' if passed else '❌'}")
        
        elif expected_status == 402:
            # Payment required checks
            checks = {
                "error_code": data.get("error_code") == "payment_required",
                "intent_id": "intent_id" in data.get("data", {}),
                "shortfall": "shortfall" in data.get("data", {}),
                "breakdown": "breakdown" in data.get("data", {}),
                "gateway": "gateway" in data.get("data", {}),
            }
            for check, passed in checks.items():
                print(f"   {check}: {'✅' if passed else '❌'}")
        
        elif expected_status == 400:
            # Error response checks
            error_code = data.get("error_code") or data.get("error", {}).get("code")
            print(f"   error_code: {error_code}")
        
        # Overall result
        passed = status_match and success_match
        results.append({
            "scenario": scenario_num,
            "description": description,
            "passed": passed,
            "status": response.status_code,
            "expected_status": expected_status
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
    print_header("PAY DUE - COMPREHENSIVE SCENARIO TESTING")
    print("Based on: plans/DUE.md")
    
    # Get rental ID
    rental_id = input("\nEnter rental ID with dues: ").strip()
    if not rental_id:
        print("❌ No rental ID provided")
        return
    
    print("\n📝 Test Instructions:")
    print("   - You'll be prompted to set wallet/points balance before each test")
    print("   - Press Enter after setting the balance")
    print("   - Tests will run automatically")
    
    input("\nPress Enter to start testing...")
    
    # ========================================================================
    # WALLET MODE SCENARIOS
    # ========================================================================
    print_header("WALLET MODE SCENARIOS")
    
    # Scenario 1: wallet + SUFFICIENT
    print("\n🔧 Setup: Set wallet balance to NPR 200.00, points to 1000")
    input("Press Enter when ready...")
    test_scenario(
        1, "wallet + SUFFICIENT",
        rental_id,
        {"payment_mode": "wallet"},
        200, True
    )
    
    # Scenario 2: wallet + INSUFFICIENT
    print("\n🔧 Setup: Set wallet balance to NPR 30.00, points to 1000")
    input("Press Enter when ready...")
    test_scenario(
        2, "wallet + INSUFFICIENT",
        rental_id,
        {"payment_mode": "wallet", "payment_method_id": KHALTI_ID},
        402, False
    )
    
    # ========================================================================
    # POINTS MODE SCENARIOS
    # ========================================================================
    print_header("POINTS MODE SCENARIOS")
    
    # Scenario 3: points + SUFFICIENT
    print("\n🔧 Setup: Set wallet balance to NPR 200.00, points to 20000")
    input("Press Enter when ready...")
    test_scenario(
        3, "points + SUFFICIENT",
        rental_id,
        {"payment_mode": "points"},
        200, True
    )
    
    # Scenario 4: points + INSUFFICIENT
    print("\n🔧 Setup: Set wallet balance to NPR 200.00, points to 2000")
    input("Press Enter when ready...")
    test_scenario(
        4, "points + INSUFFICIENT",
        rental_id,
        {"payment_mode": "points", "payment_method_id": ESEWA_ID},
        402, False
    )
    
    # ========================================================================
    # WALLET + POINTS MODE SCENARIOS
    # ========================================================================
    print_header("WALLET + POINTS MODE SCENARIOS")
    
    # Scenario 5: wallet_points + SUFFICIENT
    print("\n🔧 Setup: Set wallet balance to NPR 60.00, points to 5000")
    input("Press Enter when ready...")
    test_scenario(
        5, "wallet_points + SUFFICIENT",
        rental_id,
        {"payment_mode": "wallet_points"},
        200, True
    )
    
    # Scenario 6: wallet_points + wallet short
    print("\n🔧 Setup: Set wallet balance to NPR 20.00, points to 5000")
    input("Press Enter when ready...")
    test_scenario(
        6, "wallet_points + wallet short",
        rental_id,
        {"payment_mode": "wallet_points", "payment_method_id": KHALTI_ID},
        402, False
    )
    
    # Scenario 7: wallet_points + points short
    print("\n🔧 Setup: Set wallet balance to NPR 60.00, points to 2000")
    input("Press Enter when ready...")
    test_scenario(
        7, "wallet_points + points short",
        rental_id,
        {"payment_mode": "wallet_points", "payment_method_id": ESEWA_ID},
        402, False
    )
    
    # ========================================================================
    # DIRECT MODE SCENARIO
    # ========================================================================
    print_header("DIRECT MODE SCENARIO")
    
    # Scenario 8: direct mode
    print("\n🔧 Setup: Set wallet balance to NPR 200.00, points to 10000")
    input("Press Enter when ready...")
    test_scenario(
        8, "direct mode (force gateway)",
        rental_id,
        {"payment_mode": "direct", "payment_method_id": KHALTI_ID},
        402, False
    )
    
    # ========================================================================
    # VALIDATION ERROR SCENARIOS
    # ========================================================================
    print_header("VALIDATION ERROR SCENARIOS")
    
    # Scenario 11: direct without payment_method_id
    test_scenario(
        11, "direct without payment_method_id",
        rental_id,
        {"payment_mode": "direct"},
        400, False
    )
    
    # Scenario 12: Insufficient without payment_method_id
    print("\n🔧 Setup: Set wallet balance to NPR 30.00")
    input("Press Enter when ready...")
    test_scenario(
        12, "Insufficient without payment_method_id",
        rental_id,
        {"payment_mode": "wallet"},
        400, False
    )
    
    # Scenario 13: Invalid payment_mode
    test_scenario(
        13, "Invalid payment_mode",
        rental_id,
        {"payment_mode": "invalid_mode"},
        400, False
    )
    
    # ========================================================================
    # TEST SUMMARY
    # ========================================================================
    print_header("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    print("\n" + "="*70)
    print("DETAILED RESULTS")
    print("="*70)
    
    for r in results:
        status = "✅ PASS" if r.get("passed") else "❌ FAIL"
        print(f"{status} | Scenario {r['scenario']}: {r['description']}")
        if not r.get("passed"):
            if "error" in r:
                print(f"       Error: {r['error']}")
            else:
                print(f"       Expected: {r.get('expected_status')}, Got: {r.get('status')}")
    
    print("\n" + "="*70)
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    print("="*70)

if __name__ == "__main__":
    main()
