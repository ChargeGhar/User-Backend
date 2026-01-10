#!/bin/bash

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY2NTc1MDYyLCJpYXQiOjE3NjM5ODMwNjIsImp0aSI6IjRiY2Q0ZWYxMjIxZDQ2MzNhZDY5MDAwMTY0M2RhZjFjIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.O9YGXSNfJ4FG-UTsG91y8TGdS4WGSSEqQ6Ie9f1bC3g"

echo "=== TESTING PUT vs PATCH BEHAVIOR ==="
echo

# Function to get profile
get_profile() {
    echo "📋 GET /api/users/profile:"
    curl -X GET "http://localhost:8010/api/users/profile" \
      -H "Authorization: Bearer $TOKEN" \
      -s | jq '.data'
    echo
    
    echo "📋 GET /api/auth/me (profile section):"
    curl -X GET "http://localhost:8010/api/auth/me" \
      -H "Authorization: Bearer $TOKEN" \
      -s | jq '.data.profile'
    echo
}

# Function to test PUT
test_put() {
    local data="$1"
    local desc="$2"
    echo "🔄 PUT /api/users/profile - $desc"
    echo "Sending: $data"
    curl -X PUT "http://localhost:8010/api/users/profile" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$data" \
      -s | jq '.data'
    echo
}

# Function to test PATCH
test_patch() {
    local data="$1"
    local desc="$2"
    echo "🔄 PATCH /api/users/profile - $desc"
    echo "Sending: $data"
    curl -X PATCH "http://localhost:8010/api/users/profile" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$data" \
      -s | jq '.data'
    echo
}

# Initial state
echo "📊 INITIAL PROFILE STATE:"
get_profile

# Test 1: PUT with only full_name
echo "🧪 TEST 1: PUT with only full_name field"
test_put '{"full_name": "PUT Test Name"}' "Only full_name provided"
get_profile

# Reset to original values
echo "�� RESETTING to original values..."
test_put '{"full_name": "Janak Admin", "date_of_birth": "1990-01-01", "address": "Pokhara, Nepal", "avatar_url": "https://example.com/avatar.jpg"}' "Reset all fields"
get_profile

# Test 2: PATCH with only full_name
echo "🧪 TEST 2: PATCH with only full_name field"
test_patch '{"full_name": "PATCH Test Name"}' "Only full_name provided"
get_profile

# Test 3: PUT with explicit null values
echo "🧪 TEST 3: PUT with explicit null values"
test_put '{"full_name": "PUT With Nulls", "date_of_birth": null, "address": null}' "Explicit null values"
get_profile

# Reset again
echo "🔄 RESETTING to original values..."
test_put '{"full_name": "Janak Admin", "date_of_birth": "1990-01-01", "address": "Pokhara, Nepal", "avatar_url": "https://example.com/avatar.jpg"}' "Reset all fields"
get_profile

# Test 4: PATCH with explicit null values
echo "🧪 TEST 4: PATCH with explicit null values"
test_patch '{"full_name": "PATCH With Nulls", "date_of_birth": null, "address": null}' "Explicit null values"
get_profile

echo "=== TEST COMPLETE ==="
