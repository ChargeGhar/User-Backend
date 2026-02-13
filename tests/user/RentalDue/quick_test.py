"""
Quick Test - Failed Scenarios
"""
import requests
import json

API_URL = "http://localhost:8010"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNTgxMTMyLCJpYXQiOjE3NzA5ODkxMzIsImp0aSI6IjllZjI3NmJiYWVmZDQ0YTY5N2MzYzNlYjY4ZGM5NWYzIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.vjOTD1H-MlFy9XlITFMIVdI_SVxdCEcdOq0AvCLV56w"

# Known test data
STATION_SN = "DUMMY-SN-d2ac3931"
PREPAID_ID = "550e8400-e29b-41d4-a716-446655440001"
POSTPAID_ID = "75deede1-a812-4f22-be8a-9642821ed9e2"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("="*70)
print("QUICK TEST - Failed Scenarios")
print("="*70)

# Test 1: PREPAID + points + SUFFICIENT
print("\n1. PREPAID + points + SUFFICIENT")
print("-" * 70)

response = requests.post(
    f"{API_URL}/api/rentals/start",
    headers=headers,
    json={
        "station_sn": STATION_SN,
        "package_id": PREPAID_ID,
        "payment_mode": "points"
    }
)

print(f"HTTP: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")

if result.get('success'):
    print(f"✅ Rental: {result['data'].get('rental_code')}")
    print(f"✅ Status: {result['data'].get('status')}")
else:
    error = result.get('error_code') or result.get('error', {}).get('code')
    print(f"❌ Error: {error}")

print(json.dumps(result, indent=2)[:500])

# Test 2: PREPAID + wallet_points + SUFFICIENT  
print("\n\n2. PREPAID + wallet_points + SUFFICIENT")
print("-" * 70)

response = requests.post(
    f"{API_URL}/api/rentals/start",
    headers=headers,
    json={
        "station_sn": STATION_SN,
        "package_id": PREPAID_ID,
        "payment_mode": "wallet_points",
        "wallet_amount": "30.00",
        "points_to_use": 200
    }
)

print(f"HTTP: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")

if result.get('success'):
    print(f"✅ Rental: {result['data'].get('rental_code')}")
    print(f"✅ Status: {result['data'].get('status')}")
else:
    error = result.get('error_code') or result.get('error', {}).get('code')
    print(f"❌ Error: {error}")

print(json.dumps(result, indent=2)[:500])

# Test 3: POSTPAID + wallet + SUFFICIENT
print("\n\n3. POSTPAID + wallet + SUFFICIENT")
print("-" * 70)

response = requests.post(
    f"{API_URL}/api/rentals/start",
    headers=headers,
    json={
        "station_sn": STATION_SN,
        "package_id": POSTPAID_ID,
        "payment_mode": "wallet"
    }
)

print(f"HTTP: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")

if result.get('success'):
    print(f"✅ Rental: {result['data'].get('rental_code')}")
    print(f"✅ Status: {result['data'].get('status')}")
else:
    error = result.get('error_code') or result.get('error', {}).get('code')
    print(f"❌ Error: {error}")

print(json.dumps(result, indent=2)[:500])

print("\n" + "="*70)
print("DONE")
print("="*70)
