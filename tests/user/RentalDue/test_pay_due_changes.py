#!/usr/bin/env python3
"""Test pay-due implementation changes."""

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

def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title}")
    print('='*70)

def verify_field(data, path, expected_type, field_name):
    """Verify field exists and has correct type."""
    keys = path.split('.')
    value = data
    for key in keys:
        if key not in value:
            print(f"  ❌ Missing field: {path}")
            return False
        value = value[key]
    
    if expected_type == "string" and not isinstance(value, str):
        print(f"  ❌ {field_name}: Expected string, got {type(value).__name__}")
        return False
    elif expected_type == "int" and not isinstance(value, int):
        print(f"  ❌ {field_name}: Expected int, got {type(value).__name__}")
        return False
    elif expected_type == "bool" and not isinstance(value, bool):
        print(f"  ❌ {field_name}: Expected bool, got {type(value).__name__}")
        return False
    
    print(f"  ✅ {field_name}: {value} ({type(value).__name__})")
    return True

def test_insufficient_balance(rental_id):
    """Test wallet + INSUFFICIENT (should return HTTP 402)."""
    print_section("TEST 1: wallet + INSUFFICIENT (HTTP 402)")
    
    response = requests.post(
        f"{API_URL}/api/rentals/{rental_id}/pay-due",
        headers=headers,
        json={
            "payment_mode": "wallet",
            "payment_method_id": KHALTI_ID
        }
    )
    
    print(f"\nHTTP Status: {response.status_code}")
    data = response.json()
    
    # Verify HTTP 402
    if response.status_code != 402:
        print(f"❌ FAIL: Expected HTTP 402, got {response.status_code}")
        return False
    
    # Verify structure
    checks = [
        (data.get("success") == False, "success: false"),
        (data.get("error_code") == "payment_required", "error_code: payment_required"),
        ("data" in data, "data field exists"),
        ("error" not in data.get("data", {}), "data is flat (not nested in error)"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc}")
            all_pass = False
    
    # Verify fields
    if "data" in data:
        verify_field(data, "data.intent_id", "string", "intent_id")
        verify_field(data, "data.shortfall", "string", "shortfall")
        verify_field(data, "data.breakdown", "dict", "breakdown")
        verify_field(data, "data.breakdown.wallet_amount", "string", "breakdown.wallet_amount")
        verify_field(data, "data.breakdown.points_used", "int", "breakdown.points_used")
        verify_field(data, "data.breakdown.points_amount", "string", "breakdown.points_amount")
        verify_field(data, "data.gateway", "string", "gateway")
        verify_field(data, "data.gateway_url", "string", "gateway_url")
        
        # Check for old fields (should NOT exist)
        if "payment_breakdown" in data["data"]:
            print("  ❌ Old field 'payment_breakdown' still exists")
            all_pass = False
        else:
            print("  ✅ Old field 'payment_breakdown' removed")
    
    return all_pass

def test_sufficient_balance(rental_id):
    """Test wallet + SUFFICIENT (should return HTTP 200)."""
    print_section("TEST 2: wallet + SUFFICIENT (HTTP 200)")
    
    response = requests.post(
        f"{API_URL}/api/rentals/{rental_id}/pay-due",
        headers=headers,
        json={
            "payment_mode": "wallet"
        }
    )
    
    print(f"\nHTTP Status: {response.status_code}")
    data = response.json()
    
    # Verify HTTP 200
    if response.status_code != 200:
        print(f"❌ FAIL: Expected HTTP 200, got {response.status_code}")
        return False
    
    # Verify structure
    checks = [
        (data.get("success") == True, "success: true"),
        ("data" in data, "data field exists"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc}")
            all_pass = False
    
    # Verify fields
    if "data" in data:
        verify_field(data, "data.transaction_id", "string", "transaction_id")
        verify_field(data, "data.rental_id", "string", "rental_id")
        verify_field(data, "data.rental_code", "string", "rental_code")
        verify_field(data, "data.amount_paid", "string", "amount_paid")
        verify_field(data, "data.breakdown", "dict", "breakdown")
        verify_field(data, "data.breakdown.wallet_amount", "string", "breakdown.wallet_amount")
        verify_field(data, "data.breakdown.points_used", "int", "breakdown.points_used")
        verify_field(data, "data.breakdown.points_amount", "string", "breakdown.points_amount")
        verify_field(data, "data.payment_status", "string", "payment_status")
        verify_field(data, "data.rental_status", "string", "rental_status")
        verify_field(data, "data.account_unblocked", "bool", "account_unblocked")
        
        # Check for old fields (should NOT exist)
        old_fields = ["payment_breakdown", "wallet_used", "points_to_use"]
        for field in old_fields:
            if field in data["data"]:
                print(f"  ❌ Old field '{field}' still exists")
                all_pass = False
            else:
                print(f"  ✅ Old field '{field}' removed")
    
    return all_pass

def main():
    print_section("PAY DUE IMPLEMENTATION TEST")
    print("Testing response format changes...")
    
    # Get rental ID from user
    rental_id = input("\nEnter rental ID with dues: ").strip()
    
    if not rental_id:
        print("❌ No rental ID provided")
        return
    
    # Test 1: Insufficient balance (HTTP 402)
    print("\n📝 Setup: Set wallet balance to NPR 30.00")
    input("Press Enter after setting balance...")
    
    test1_pass = test_insufficient_balance(rental_id)
    
    # Test 2: Sufficient balance (HTTP 200)
    print("\n📝 Setup: Set wallet balance to NPR 200.00")
    input("Press Enter after setting balance...")
    
    test2_pass = test_sufficient_balance(rental_id)
    
    # Summary
    print_section("TEST SUMMARY")
    print(f"Test 1 (HTTP 402): {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Test 2 (HTTP 200): {'✅ PASS' if test2_pass else '❌ FAIL'}")
    
    if test1_pass and test2_pass:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed")

if __name__ == "__main__":
    main()
