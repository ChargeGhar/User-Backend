echo "🧪 Comprehensive Authentication Flow Test"
echo "========================================"
echo ""

# Step 1: Request OTP for a new user
echo "📱 Step 1: Request OTP for new user..."
OTP_RESPONSE=$(curl -s -X POST http://localhost:8010/api/auth/otp/request \
    -H "Content-Type: application/json" \
    -d '{"identifier": "test.blacklist@example.com"}')

echo "OTP Response: $(echo "$OTP_RESPONSE" | jq -c .)"

if echo "$OTP_RESPONSE" | jq -e '.success' > /dev/null; then
    # Get OTP from Redis
    OTP=$(docker-compose exec -T api python manage.py shell -c "
from django.core.cache import cache
otp_data = cache.get('unified_otp:test.blacklist@example.com')
if otp_data:
    print(otp_data['otp'])
else:
    print('NOT_FOUND')
" 2>/dev/null | tail -1)

    if [ "$OTP" != "NOT_FOUND" ]; then
        echo "✅ Got OTP: $OTP"
        echo ""
        
        # Step 2: Verify OTP
        echo "🔐 Step 2: Verify OTP..."
        VERIFY_RESPONSE=$(curl -s -X POST http://localhost:8010/api/auth/otp/verify \
            -H "Content-Type: application/json" \
            -d "{\"identifier\": \"test.blacklist@example.com\", \"otp\": \"$OTP\"}")
        
        VERIFICATION_TOKEN=$(echo "$VERIFY_RESPONSE" | jq -r '.data.verification_token')
        echo "✅ Verification Token: ${VERIFICATION_TOKEN:0:20}..."
        echo ""
        
        # Step 3: Complete Registration
        echo "📝 Step 3: Complete Registration..."
        COMPLETE_RESPONSE=$(curl -s -X POST http://localhost:8010/api/auth/complete \
            -H "Content-Type: application/json" \
            -d "{\"identifier\": \"test.blacklist@example.com\", \"verification_token\": \"$VERIFICATION_TOKEN\", \"username\": \"BlacklistTestUser\"}")
        
        ACCESS_TOKEN=$(echo "$COMPLETE_RESPONSE" | jq -r '.data.tokens.access')
        REFRESH_TOKEN=$(echo "$COMPLETE_RESPONSE" | jq -r '.data.tokens.refresh')
        
        echo "✅ Registration successful!"
        echo "Access Token: ${ACCESS_TOKEN:0:50}..."
        echo "Refresh Token: ${REFRESH_TOKEN:0:50}..."
        echo ""
        
        # Step 4: Test Token Refresh
        echo "🔄 Step 4: Test Token Refresh..."
        REFRESH_RESPONSE=$(curl -s -X POST http://localhost:8010/api/auth/refresh \
            -H "Content-Type: application/json" \
            -d "{\"refresh\": \"$REFRESH_TOKEN\"}")
        
        if echo "$REFRESH_RESPONSE" | jq -e '.success' > /dev/null; then
            NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.data.access')
            NEW_REFRESH_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.data.refresh')
            echo "✅ Token refresh successful!"
            echo "New Access Token: ${NEW_ACCESS_TOKEN:0:50}..."
            echo "New Refresh Token: ${NEW_REFRESH_TOKEN:0:50}..."
            echo ""
            
            # Step 5: Test Logout with Blacklisting
            echo "🚪 Step 5: Test Logout with Blacklisting..."
            LOGOUT_RESPONSE=$(curl -s -X POST http://localhost:8010/api/auth/logout \
                -H "Authorization: Bearer $NEW_ACCESS_TOKEN" \
                -H "Content-Type: application/json" \
                -d "{\"refresh_token\": \"$NEW_REFRESH_TOKEN\"}")
            
            if echo "$LOGOUT_RESPONSE" | jq -e '.success' > /dev/null; then
                echo "✅ Logout successful!"
                echo ""
                
                # Step 6: Test Blacklisted Token
                echo "🔒 Step 6: Test Blacklisted Token (should fail)..."
                BLACKLIST_TEST=$(curl -s -X POST http://localhost:8010/api/auth/refresh \
                    -H "Content-Type: application/json" \
                    -d "{\"refresh\": \"$NEW_REFRESH_TOKEN\"}")
                
                echo "Blacklist Test Response:"
                echo "$BLACKLIST_TEST" | jq .
                
                if echo "$BLACKLIST_TEST" | jq -e '.success' > /dev/null; then
                    echo "❌ FAILED: Token should be blacklisted!"
                else
                    echo "✅ SUCCESS: Token is properly blacklisted!"
                fi
            else
                echo "❌ Logout failed"
                echo "$LOGOUT_RESPONSE" | jq .
            fi
        else
            echo "❌ Token refresh failed"
            echo "$REFRESH_RESPONSE" | jq .
        fi
    else
        echo "❌ Could not get OTP"
    fi
else
    echo "❌ OTP request failed"
    echo "$OTP_RESPONSE" | jq .
fi