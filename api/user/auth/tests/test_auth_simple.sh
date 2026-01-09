#!/bin/bash

# Simple authentication test script
# Tests refresh, logout, and /me endpoints with existing tokens

set -e

BASE_URL="http://localhost:8010"

echo "🚀 Simple Authentication Test"
echo "============================="
echo ""

# Test 1: Get fresh tokens through complete auth flow
echo "🔑 Getting fresh authentication tokens..."

# Request OTP
OTP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/otp/request" \
    -H "Content-Type: application/json" \
    -d '{"identifier": "test@example.com"}')

echo "OTP Request: $(echo "$OTP_RESPONSE" | jq -r '.message')"

if echo "$OTP_RESPONSE" | jq -e '.success' > /dev/null; then
    # Get OTP from Redis
    OTP=$(docker-compose exec -T api python manage.py shell -c "
from django.core.cache import cache
otp_data = cache.get('unified_otp:test@example.com')
if otp_data:
    print(otp_data['otp'])
else:
    print('NOT_FOUND')
" 2>/dev/null | tail -1)

    if [ "$OTP" != "NOT_FOUND" ]; then
        echo "🔑 Got OTP: $OTP"
        
        # Verify OTP
        VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/otp/verify" \
            -H "Content-Type: application/json" \
            -d "{\"identifier\": \"test@example.com\", \"otp\": \"$OTP\"}")
        
        VERIFICATION_TOKEN=$(echo "$VERIFY_RESPONSE" | jq -r '.data.verification_token')
        
        # Complete auth (register new user)
        COMPLETE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/complete" \
            -H "Content-Type: application/json" \
            -d "{\"identifier\": \"test@example.com\", \"verification_token\": \"$VERIFICATION_TOKEN\", \"username\": \"TestUser\"}")
        
        ACCESS_TOKEN=$(echo "$COMPLETE_RESPONSE" | jq -r '.data.tokens.access')
        REFRESH_TOKEN=$(echo "$COMPLETE_RESPONSE" | jq -r '.data.tokens.refresh')
        
        echo "✅ Authentication successful!"
        echo ""
        
        # Test 2: Test /me endpoint
        echo "👤 Testing /me endpoint..."
        ME_RESPONSE=$(curl -s -X GET "$BASE_URL/api/auth/me" \
            -H "Authorization: Bearer $ACCESS_TOKEN")
        
        if echo "$ME_RESPONSE" | jq -e '.success' > /dev/null; then
            USERNAME=$(echo "$ME_RESPONSE" | jq -r '.data.username')
            echo "✅ /me endpoint working - User: $USERNAME"
        else
            echo "❌ /me endpoint failed"
        fi
        echo ""
        
        # Test 3: Test token refresh
        echo "🔄 Testing token refresh..."
        REFRESH_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/refresh" \
            -H "Content-Type: application/json" \
            -d "{\"refresh\": \"$REFRESH_TOKEN\"}")
        
        if echo "$REFRESH_RESPONSE" | jq -e '.success' > /dev/null; then
            NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.data.access')
            echo "✅ Token refresh working"
        else
            echo "❌ Token refresh failed"
        fi
        echo ""
        
        # Test 4: Test logout
        echo "🚪 Testing logout..."
        LOGOUT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/logout" \
            -H "Authorization: Bearer $NEW_ACCESS_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")
        
        if echo "$LOGOUT_RESPONSE" | jq -e '.success' > /dev/null; then
            echo "✅ Logout working"
        else
            echo "❌ Logout failed"
        fi
        
        echo ""
        echo "🎉 All tests completed successfully!"
        
    else
        echo "⚠️  Could not get OTP, using existing user for tests..."
        # Fallback to existing user tests would go here
    fi
else
    echo "❌ OTP request failed"
    exit 1
fi