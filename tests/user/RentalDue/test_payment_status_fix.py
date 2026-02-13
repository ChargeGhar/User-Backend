#!/usr/bin/env python3
"""
Test payment_status fix for OVERDUE rentals
"""

import requests
import subprocess

API_URL = "http://localhost:8010"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNTgxMTMyLCJpYXQiOjE3NzA5ODkxMzIsImp0aSI6IjllZjI3NmJiYWVmZDQ0YTY5N2MzYzNlYjY4ZGM5NWYzIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.vjOTD1H-MlFy9XlITFMIVdI_SVxdCEcdOq0AvCLV56w"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("="*70)
print("TEST: payment_status Fix for OVERDUE Rentals")
print("="*70)

rental_id = input("\nEnter OVERDUE rental ID: ").strip()
if not rental_id:
    print("❌ No rental ID provided")
    exit(1)

# Check rental status before payment
print("\n1. Checking rental status BEFORE payment...")
cmd = f"""
docker exec cg-api-local python manage.py shell -c "
from api.user.rentals.models import Rental
rental = Rental.objects.get(id='{rental_id}')
print(f'Status: {{rental.status}}')
print(f'Payment Status: {{rental.payment_status}}')
print(f'Ended At: {{rental.ended_at}}')
print(f'Overdue Amount: {{rental.current_overdue_amount}}')
" 2>/dev/null
"""
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)

# Set sufficient balance
print("\n2. Setting wallet balance to NPR 5000.00...")
cmd = """
docker exec cg-api-local python manage.py shell -c "
from api.user.auth.models import User
from api.user.payments.models import Wallet
from decimal import Decimal

user = User.objects.get(id=1)
wallet, _ = Wallet.objects.get_or_create(user=user)
wallet.balance = Decimal('5000.00')
wallet.save()
print(f'Wallet: {wallet.balance}')
" 2>/dev/null
"""
subprocess.run(cmd, shell=True, capture_output=True)
print("✅ Balance set")

# Pay dues
print("\n3. Paying rental dues...")
response = requests.post(
    f"{API_URL}/api/rentals/{rental_id}/pay-due",
    headers=headers,
    json={"payment_mode": "wallet"},
    timeout=15
)

print(f"HTTP Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"✅ Payment successful")
    print(f"   Transaction ID: {data['data'].get('transaction_id')}")
    print(f"   Amount Paid: {data['data'].get('amount_paid')}")
    print(f"   Payment Status: {data['data'].get('payment_status')}")
    print(f"   Rental Status: {data['data'].get('rental_status')}")
else:
    print(f"❌ Payment failed: {response.json()}")
    exit(1)

# Check rental status after payment
print("\n4. Checking rental status AFTER payment...")
cmd = f"""
docker exec cg-api-local python manage.py shell -c "
from api.user.rentals.models import Rental
rental = Rental.objects.get(id='{rental_id}')
print(f'Status: {{rental.status}}')
print(f'Payment Status: {{rental.payment_status}}')
print(f'Ended At: {{rental.ended_at}}')
print(f'Overdue Amount: {{rental.overdue_amount}}')
" 2>/dev/null
"""
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)

# Verify fix
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

cmd = f"""
docker exec cg-api-local python manage.py shell -c "
from api.user.rentals.models import Rental
rental = Rental.objects.get(id='{rental_id}')

# Check if payment_status is PAID
if rental.payment_status == 'PAID':
    print('✅ payment_status is PAID (correct)')
else:
    print(f'❌ payment_status is {{rental.payment_status}} (should be PAID)')

# Check if overdue_amount is 0
if rental.overdue_amount == 0:
    print('✅ overdue_amount is 0 (correct)')
else:
    print(f'❌ overdue_amount is {{rental.overdue_amount}} (should be 0)')

# Check status based on return
if rental.ended_at:
    if rental.status == 'COMPLETED':
        print('✅ status is COMPLETED (powerbank returned)')
    else:
        print(f'❌ status is {{rental.status}} (should be COMPLETED)')
else:
    if rental.status == 'OVERDUE':
        print('✅ status is OVERDUE (powerbank not returned)')
    else:
        print(f'⚠️  status is {{rental.status}} (expected OVERDUE)')
" 2>/dev/null
"""
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
