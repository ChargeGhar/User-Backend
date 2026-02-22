#!/bin/bash
# ============================================================================
# Quick Start Testing Script
# ============================================================================
# Purpose: Automated setup and execution of rental testing
# Usage: ./quick_test.sh [scenario]
# Scenarios: prepaid, postpaid, postpaid-late, cancel
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8010"
ADMIN_EMAIL="janak@powerbank.com"
ADMIN_PASSWORD="5060"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================================
# Step 1: Admin Login
# ============================================================================

admin_login() {
    print_header "Step 1: Admin Login"

    response=$(curl -s -X 'POST' \
        "${BASE_URL}/api/admin/login" \
        -H 'accept: application/json' \
        -H 'Content-Type: multipart/form-data' \
        -F "email=${ADMIN_EMAIL}" \
        -F "password=${ADMIN_PASSWORD}")

    TOKEN=$(echo $response | jq -r '.data.access_token')
    USER_ID=$(echo $response | jq -r '.data.user_id')

    if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
        print_success "Admin login successful"
        print_info "User ID: $USER_ID"
        export TOKEN
        export USER_ID
    else
        print_error "Admin login failed"
        echo $response | jq '.'
        exit 1
    fi
}

# ============================================================================
# Step 2: Get User Info
# ============================================================================

get_user_info() {
    print_header "Step 2: Get User Info & Balances"

    # Get user info
    user_info=$(curl -s -X 'GET' \
        "${BASE_URL}/api/auth/me" \
        -H "Authorization: Bearer $TOKEN")

    echo $user_info | jq '.'

    # Get wallet balance
    wallet_info=$(curl -s -X 'GET' \
        "${BASE_URL}/api/users/wallet" \
        -H "Authorization: Bearer $TOKEN")

    WALLET_BALANCE=$(echo $wallet_info | jq -r '.data.balance')
    print_info "Wallet Balance: NPR $WALLET_BALANCE"

    # Get points (from history endpoint)
    points_info=$(curl -s -X 'GET' \
        "${BASE_URL}/api/points/history?page=1&page_size=1" \
        -H "Authorization: Bearer $TOKEN")

    echo $points_info | jq '.data.pagination.total_points // 0' > /dev/null 2>&1
    print_success "User info retrieved"
}

# ============================================================================
# Step 3: Get Packages
# ============================================================================

get_packages() {
    print_header "Step 3: Get Available Packages"

    packages=$(curl -s -X 'GET' \
        "${BASE_URL}/api/rentals/packages" \
        -H "Authorization: Bearer $TOKEN")

    echo $packages | jq '.data.packages[] | {id, name, payment_model, price, duration_minutes}'

    # Extract package IDs
    PREPAID_PACKAGE_ID=$(echo $packages | jq -r '.data.packages[] | select(.payment_model == "PREPAID") | .id' | head -1)
    POSTPAID_PACKAGE_ID=$(echo $packages | jq -r '.data.packages[] | select(.payment_model == "POSTPAID") | .id' | head -1)

    if [ -n "$PREPAID_PACKAGE_ID" ]; then
        print_success "Prepaid Package ID: $PREPAID_PACKAGE_ID"
        export PREPAID_PACKAGE_ID
    fi

    if [ -n "$POSTPAID_PACKAGE_ID" ]; then
        print_success "Postpaid Package ID: $POSTPAID_PACKAGE_ID"
        export POSTPAID_PACKAGE_ID
    else
        print_warning "No postpaid package found"
    fi
}

# ============================================================================
# Step 4: Get Stations
# ============================================================================

get_stations() {
    print_header "Step 4: Get Available Stations"

    stations=$(curl -s -X 'GET' \
        "${BASE_URL}/api/stations" \
        -H "Authorization: Bearer $TOKEN")

    echo $stations | jq '.data.stations[] | {serial_number, station_name, status, available_powerbanks}' | head -20

    STATION_SN=$(echo $stations | jq -r '.data.stations[] | select(.status == "ONLINE" and .available_powerbanks > 0) | .serial_number' | head -1)

    if [ -n "$STATION_SN" ]; then
        print_success "Station Serial: $STATION_SN"
        export STATION_SN
    else
        print_error "No available station found"
        exit 1
    fi
}

# ============================================================================
# Step 5: Start Rental
# ============================================================================

start_rental() {
    local payment_model=$1
    print_header "Step 5: Start $payment_model Rental"

    if [ "$payment_model" == "PREPAID" ]; then
        PACKAGE_ID=$PREPAID_PACKAGE_ID
    else
        PACKAGE_ID=$POSTPAID_PACKAGE_ID
    fi

    if [ -z "$PACKAGE_ID" ]; then
        print_error "Package ID not found for $payment_model"
        exit 1
    fi

    response=$(curl -s -X 'POST' \
        "${BASE_URL}/api/rentals/start" \
        -H "Authorization: Bearer $TOKEN" \
        -H 'Content-Type: application/json' \
        -d "{
            \"station_sn\": \"$STATION_SN\",
            \"package_id\": \"$PACKAGE_ID\",
            \"payment_mode\": \"wallet_points\"
        }")

    echo $response | jq '.'

    RENTAL_ID=$(echo $response | jq -r '.data.rental_id')
    RENTAL_CODE=$(echo $response | jq -r '.data.rental_code')

    if [ "$RENTAL_CODE" != "null" ] && [ -n "$RENTAL_CODE" ]; then
        print_success "Rental started successfully"
        print_info "Rental Code: $RENTAL_CODE"
        print_info "Rental ID: $RENTAL_ID"
        export RENTAL_ID
        export RENTAL_CODE
    else
        print_error "Failed to start rental"
        exit 1
    fi
}

# ============================================================================
# Step 6: Get Active Rental
# ============================================================================

get_active_rental() {
    print_header "Step 6: Get Active Rental"

    response=$(curl -s -X 'GET' \
        "${BASE_URL}/api/rentals/active" \
        -H "Authorization: Bearer $TOKEN")

    echo $response | jq '.'

    STATUS=$(echo $response | jq -r '.data.status')
    PAYMENT_STATUS=$(echo $response | jq -r '.data.payment_status')

    print_info "Status: $STATUS"
    print_info "Payment Status: $PAYMENT_STATUS"
}

# ============================================================================
# Step 7: Make Rental Overdue (for testing)
# ============================================================================

make_rental_overdue() {
    print_header "Step 7: Make Rental Overdue (Testing)"

    print_warning "Making rental overdue by 2 hours..."

    docker exec -i cg-api-local python manage.py shell <<EOF
from api.user.rentals.models import Rental
from django.utils import timezone
from datetime import timedelta

rental = Rental.objects.get(rental_code='$RENTAL_CODE')
rental.due_at = timezone.now() - timedelta(hours=2)
rental.save()
print(f"Rental {rental.rental_code} is now overdue by 2 hours")
EOF

    print_success "Rental is now overdue"

    # Check active rental again
    sleep 2
    get_active_rental
}

# ============================================================================
# Step 8: Return Rental
# ============================================================================

return_rental() {
    print_header "Step 8: Return Rental via IoT Script"

    print_info "Running IoT return script..."

    cd "$(dirname "$0")/../.."
    python tests/OLD/test_iot_return.py "$RENTAL_CODE"

    print_success "Return process completed"
}

# ============================================================================
# Step 9: Pay Due (if needed)
# ============================================================================

pay_due() {
    print_header "Step 9: Pay Outstanding Due"

    response=$(curl -s -X 'POST' \
        "${BASE_URL}/api/rentals/${RENTAL_ID}/pay-due" \
        -H "Authorization: Bearer $TOKEN" \
        -H 'Content-Type: application/json' \
        -d '{
            "payment_mode": "wallet_points"
        }')

    echo $response | jq '.'

    SUCCESS=$(echo $response | jq -r '.success')

    if [ "$SUCCESS" == "true" ]; then
        print_success "Payment successful"
    else
        ERROR_CODE=$(echo $response | jq -r '.error_code')
        if [ "$ERROR_CODE" == "payment_required" ]; then
            print_warning "Payment gateway required (insufficient balance)"
        else
            print_error "Payment failed: $ERROR_CODE"
        fi
    fi
}

# ============================================================================
# Step 10: Get Rental History
# ============================================================================

get_rental_history() {
    print_header "Step 10: Get Rental History"

    response=$(curl -s -X 'GET' \
        "${BASE_URL}/api/rentals/history?page=1&page_size=5" \
        -H "Authorization: Bearer $TOKEN")

    echo $response | jq '.data.rentals[] | {rental_code, status, payment_status, amount_paid, overdue_amount, is_returned_on_time}'

    print_success "History retrieved"
}

# ============================================================================
# Step 11: Cancel Rental
# ============================================================================

cancel_rental() {
    print_header "Step 11: Cancel Rental"

    response=$(curl -s -X 'POST' \
        "${BASE_URL}/api/rentals/${RENTAL_ID}/cancel" \
        -H "Authorization: Bearer $TOKEN" \
        -H 'Content-Type: application/json' \
        -d '{
            "reason": "Testing cancellation flow"
        }')

    echo $response | jq '.'

    SUCCESS=$(echo $response | jq -r '.success')

    if [ "$SUCCESS" == "true" ]; then
        print_success "Rental cancelled successfully"
    else
        print_error "Cancellation failed"
    fi
}

# ============================================================================
# Database Verification
# ============================================================================

verify_database() {
    print_header "Database Verification"

    print_info "Checking rental in database..."

    docker exec -i cg-db-local psql -U postgres -d chargeGhar <<EOF
SELECT
    rental_code,
    status,
    payment_status,
    amount_paid,
    overdue_amount,
    is_returned_on_time
FROM rentals
WHERE rental_code = '$RENTAL_CODE';
EOF

    print_info "Checking transactions..."

    docker exec -i cg-db-local psql -U postgres -d chargeGhar <<EOF
SELECT
    transaction_id,
    transaction_type,
    amount,
    status,
    payment_method_type
FROM transactions
WHERE related_rental_id = '$RENTAL_ID'
ORDER BY created_at;
EOF
}

# ============================================================================
# Test Scenarios
# ============================================================================

test_prepaid() {
    print_header "TEST SCENARIO: Prepaid Rental (On-Time Return)"

    admin_login
    get_user_info
    get_packages
    get_stations
    start_rental "PREPAID"
    sleep 2
    get_active_rental
    sleep 2
    return_rental
    sleep 2
    get_rental_history
    verify_database

    print_success "Prepaid test completed!"
}

test_postpaid() {
    print_header "TEST SCENARIO: Postpaid Rental (On-Time Return)"

    admin_login
    get_user_info
    get_packages
    get_stations
    start_rental "POSTPAID"
    sleep 2
    get_active_rental
    sleep 2
    return_rental
    sleep 2
    get_rental_history
    verify_database

    print_success "Postpaid test completed!"
}

test_postpaid_late() {
    print_header "TEST SCENARIO: Postpaid Rental (Late Return)"

    admin_login
    get_user_info
    get_packages
    get_stations
    start_rental "POSTPAID"
    sleep 2
    get_active_rental
    make_rental_overdue
    sleep 2
    return_rental
    sleep 2

    # Try to pay due if needed
    print_info "Attempting to pay due..."
    pay_due
    sleep 2

    get_rental_history
    verify_database

    print_success "Postpaid late test completed!"
}

test_cancel() {
    print_header "TEST SCENARIO: Rental Cancellation"

    admin_login
    get_user_info
    get_packages
    get_stations
    start_rental "POSTPAID"
    sleep 2
    get_active_rental
    sleep 2
    cancel_rental
    sleep 2
    get_rental_history
    verify_database

    print_success "Cancellation test completed!"
}

# ============================================================================
# Main Script
# ============================================================================

main() {
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed. Please install jq first."
        exit 1
    fi

    # Check if Docker is running
    if ! docker ps &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    # Parse scenario argument
    SCENARIO=${1:-"postpaid"}

    case $SCENARIO in
        prepaid)
            test_prepaid
            ;;
        postpaid)
            test_postpaid
            ;;
        postpaid-late)
            test_postpaid_late
            ;;
        cancel)
            test_cancel
            ;;
        *)
            print_error "Unknown scenario: $SCENARIO"
            echo "Usage: $0 [prepaid|postpaid|postpaid-late|cancel]"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
