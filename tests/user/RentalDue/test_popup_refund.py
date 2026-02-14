#!/usr/bin/env python3
"""
Simple test for popup failure refund
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_popup_failure_refund():
    print("=== Testing Popup Failure Refund ===\n")
    
    # Test data
    user_id = 1
    station_sn = "DUMMY-SN-d2ac3931"
    package_id = "550e8400-e29b-41d4-a716-446655440000"  # NPR 50 PREPAID
    
    # Login
    login_response = requests.post(f"{API_URL}/api/auth/login/", json={
        "email": "janak@powerbank.com",
        "password": "janak123"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current balance
    balance_response = requests.get(f"{API_URL}/api/payments/wallet/balance/", headers=headers)
    if balance_response.status_code == 200:
        initial_balance = balance_response.json()
        print(f"Initial Balance:")
        print(f"  Wallet: NPR {initial_balance.get('balance', 0)}")
        print(f"  Points: {initial_balance.get('points', 0)}")
    
    # Start rental with combination payment
    rental_data = {
        "station_sn": station_sn,
        "package_id": package_id,
        "payment_mode": "wallet_points",
        "wallet_amount": "30.00",
        "points_to_use": 200
    }
    
    print(f"\nStarting rental with combination payment:")
    print(f"  Wallet: NPR 30.00")
    print(f"  Points: 200 (NPR 20.00)")
    print(f"  Total: NPR 50.00")
    
    rental_response = requests.post(f"{API_URL}/api/rentals/start/", json=rental_data, headers=headers)
    
    print(f"\nRental Response: {rental_response.status_code}")
    
    if rental_response.status_code == 200:
        rental_result = rental_response.json()
        print(f"✅ Rental started successfully")
        print(f"Rental Code: {rental_result.get('rental_code')}")
        print(f"Status: {rental_result.get('status')}")
        
        # Check if payment was processed
        if rental_result.get('payment_breakdown'):
            breakdown = rental_result['payment_breakdown']
            print(f"Payment Breakdown:")
            print(f"  Wallet: NPR {breakdown.get('wallet_amount')}")
            print(f"  Points: {breakdown.get('points_used')} ({breakdown.get('points_amount')} NPR)")
        
        return True
    
    elif rental_response.status_code == 402:
        print(f"❌ Payment required (insufficient balance)")
        print(f"Response: {rental_response.json()}")
        return False
    
    else:
        print(f"❌ Rental failed: {rental_response.status_code}")
        print(f"Response: {rental_response.json()}")
        return False

if __name__ == "__main__":
    test_popup_failure_refund()
