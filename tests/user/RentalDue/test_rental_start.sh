#!/bin/bash
# Rental Start Testing Script
# Tests all 24 scenarios from plans/Rental.md

API_URL="http://localhost:8010"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNTgxMTMyLCJpYXQiOjE3NzA5ODkxMzIsImp0aSI6IjllZjI3NmJiYWVmZDQ0YTY5N2MzYzNlYjY4ZGM5NWYzIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.vjOTD1H-MlFy9XlITFMIVdI_SVxdCEcdOq0AvCLV56w"

echo "=== Rental Start Testing ==="
echo "Date: $(date)"
echo ""

# Function to make API call
test_scenario() {
    local scenario=$1
    local station_sn=$2
    local package_id=$3
    local payment_mode=$4
    local payment_method_id=$5
    local wallet_amount=$6
    local points_to_use=$7
    
    echo "=== Scenario $scenario ==="
    
    # Build request body
    local body="{\"station_sn\":\"$station_sn\",\"package_id\":\"$package_id\",\"payment_mode\":\"$payment_mode\""
    
    if [ -n "$payment_method_id" ]; then
        body="$body,\"payment_method_id\":\"$payment_method_id\""
    fi
    
    if [ -n "$wallet_amount" ]; then
        body="$body,\"wallet_amount\":\"$wallet_amount\""
    fi
    
    if [ -n "$points_to_use" ]; then
        body="$body,\"points_to_use\":$points_to_use"
    fi
    
    body="$body}"
    
    echo "Request: $body"
    
    # Make request
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST \
        "$API_URL/api/rentals/start" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$body")
    
    # Extract HTTP code
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')
    
    echo "HTTP Status: $http_code"
    echo "Response:"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    echo ""
    echo "---"
    echo ""
}

# Get database info first
echo "=== Getting Database Info ==="
docker exec cg-api-local python manage.py shell -c "
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.rentals.models import RentalPackage
from api.user.stations.models import Station

user = User.objects.get(id=1)
wallet = Wallet.objects.filter(user=user).first()
print(f'User ID: {user.id}')
print(f'Wallet Balance: {wallet.balance if wallet else 0}')

# Get first PREPAID and POSTPAID package
prepaid = RentalPackage.objects.filter(is_active=True, payment_model='PREPAID').first()
postpaid = RentalPackage.objects.filter(is_active=True, payment_model='POSTPAID').first()
print(f'PREPAID Package: {prepaid.id} - NPR {prepaid.price}' if prepaid else 'No PREPAID package')
print(f'POSTPAID Package: {postpaid.id} - NPR {postpaid.price}' if postpaid else 'No POSTPAID package')

# Get first online station
station = Station.objects.filter(status='ONLINE', is_maintenance=False).first()
print(f'Station: {station.serial_number}' if station else 'No station')
" 2>/dev/null

echo ""
echo "=== Starting Tests ==="
echo ""

# TODO: Replace these with actual values from database
STATION_SN="STN001"
PREPAID_PKG="pkg-123"
POSTPAID_PKG="pkg-456"
PAYMENT_METHOD="pm-khalti-123"

# Scenario 1: PREPAID + wallet + SUFFICIENT
# TODO: Set wallet balance to 100 NPR
test_scenario "1: PREPAID + wallet + SUFFICIENT" \
    "$STATION_SN" "$PREPAID_PKG" "wallet" "" "" ""

# Scenario 2: PREPAID + wallet + INSUFFICIENT
# TODO: Set wallet balance to 20 NPR
test_scenario "2: PREPAID + wallet + INSUFFICIENT" \
    "$STATION_SN" "$PREPAID_PKG" "wallet" "$PAYMENT_METHOD" "" ""

echo "=== Testing Complete ==="
