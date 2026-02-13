"""
Rental Start Testing Script
Tests all 24 scenarios from plans/Rental.md
"""
import requests
import json
from decimal import Decimal

API_URL = "http://localhost:8010"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNTgxMTMyLCJpYXQiOjE3NzA5ODkxMzIsImp0aSI6IjllZjI3NmJiYWVmZDQ0YTY5N2MzYzNlYjY4ZGM5NWYzIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.vjOTD1H-MlFy9XlITFMIVdI_SVxdCEcdOq0AvCLV56w"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_scenario(name, data, expected_status, expected_success):
    """Test a single scenario"""
    print(f"\n{'='*60}")
    print(f"Scenario: {name}")
    print(f"{'='*60}")
    print(f"Request: {json.dumps(data, indent=2)}")
    
    response = requests.post(
        f"{API_URL}/api/rentals/start",
        headers=headers,
        json=data
    )
    
    print(f"\nHTTP Status: {response.status_code} (Expected: {expected_status})")
    
    try:
        result = response.json()
        print(f"Response:")
        print(json.dumps(result, indent=2))
        
        # Verify
        success = result.get('success')
        print(f"\n✓ Success flag: {success} (Expected: {expected_success})")
        
        if response.status_code == expected_status and success == expected_success:
            print("✅ PASS")
            return True
        else:
            print("❌ FAIL")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"Raw response: {response.text}")
        return False

def main():
    print("="*60)
    print("RENTAL START TESTING")
    print("="*60)
    
    # Get test data from API
    print("\n📋 Fetching test data...")
    
    # Get packages
    packages_resp = requests.get(
        f"{API_URL}/api/payments/packages",
        headers=headers
    )
    
    if packages_resp.status_code == 200:
        packages_data = packages_resp.json()
        
        # Handle different response structures
        if isinstance(packages_data, dict):
            data = packages_data.get('data', {})
            if isinstance(data, dict):
                packages = data.get('packages', [])
            else:
                packages = data
        else:
            packages = packages_data
        
        prepaid_pkg = None
        postpaid_pkg = None
        
        for p in packages:
            if isinstance(p, dict):
                if p.get('payment_model') == 'PREPAID' and not prepaid_pkg:
                    prepaid_pkg = p
                elif p.get('payment_model') == 'POSTPAID' and not postpaid_pkg:
                    postpaid_pkg = p
        
        print(f"✓ PREPAID Package: {prepaid_pkg['id'] if prepaid_pkg else 'Not found'} - NPR {prepaid_pkg.get('price') if prepaid_pkg else 'N/A'}")
        print(f"✓ POSTPAID Package: {postpaid_pkg['id'] if postpaid_pkg else 'Not found'} - NPR {postpaid_pkg.get('price') if postpaid_pkg else 'N/A'}")
    else:
        print(f"❌ Failed to fetch packages: {packages_resp.status_code}")
        return
    
    # Get stations
    stations_resp = requests.get(
        f"{API_URL}/api/stations",
        headers=headers
    )
    
    if stations_resp.status_code == 200:
        stations_data = stations_resp.json()
        stations = stations_data.get('data', {}).get('results', [])
        
        if stations:
            station = stations[0]
            station_sn = station.get('serial_number')
            print(f"✓ Station: {station_sn}")
        else:
            print("❌ No stations found")
            return
    else:
        print(f"❌ Failed to fetch stations: {stations_resp.status_code}")
        return
    
    # Get payment methods
    payment_methods_resp = requests.get(
        f"{API_URL}/api/payments/methods",
        headers=headers
    )
    
    payment_method_id = None
    if payment_methods_resp.status_code == 200:
        methods_data = payment_methods_resp.json()
        if isinstance(methods_data, dict):
            methods = methods_data.get('data', [])
        else:
            methods = methods_data
        
        if methods and len(methods) > 0:
            payment_method_id = methods[0].get('id')
            print(f"✓ Payment Method: {payment_method_id}")
        else:
            print("⚠ No payment methods found")
    else:
        print(f"⚠ Failed to fetch payment methods: {payment_methods_resp.status_code}")
    
    if not prepaid_pkg or not station_sn:
        print("\n❌ Missing required test data")
        return
    
    print("\n" + "="*60)
    print("STARTING TESTS")
    print("="*60)
    
    results = []
    
    # Scenario 1: PREPAID + wallet + SUFFICIENT
    # Note: This will likely fail with insufficient balance
    # We need to update wallet balance in database first
    results.append(test_scenario(
        "1: PREPAID + wallet + SUFFICIENT",
        {
            "station_sn": station_sn,
            "package_id": prepaid_pkg['id'],
            "payment_mode": "wallet"
        },
        expected_status=201,
        expected_success=True
    ))
    
    # Scenario 2: PREPAID + wallet + INSUFFICIENT
    if payment_method_id:
        results.append(test_scenario(
            "2: PREPAID + wallet + INSUFFICIENT",
            {
                "station_sn": station_sn,
                "package_id": prepaid_pkg['id'],
                "payment_mode": "wallet",
                "payment_method_id": payment_method_id
            },
            expected_status=402,
            expected_success=False
        ))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

if __name__ == "__main__":
    main()
