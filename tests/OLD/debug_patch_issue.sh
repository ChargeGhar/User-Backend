#!/bin/bash

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY2NTc1MDYyLCJpYXQiOjE3NjM5ODMwNjIsImp0aSI6IjRiY2Q0ZWYxMjIxZDQ2MzNhZDY5MDAwMTY0M2RhZjFjIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.O9YGXSNfJ4FG-UTsG91y8TGdS4WGSSEqQ6Ie9f1bC3g"

echo "=== DEBUGGING PATCH ISSUE ==="
echo

# Reset to known state
echo "🔄 RESETTING to known state..."
curl -X PUT "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Original Name", "date_of_birth": "1990-01-01", "address": "Original Address", "avatar_url": "https://example.com/original.jpg"}' \
  -s > /dev/null
echo "Reset complete"
echo

# Show current state
echo "�� CURRENT PROFILE STATE:"
curl -X GET "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq '.data'
echo

echo "🧪 TEST 1: PATCH with ONLY full_name (should preserve others)"
curl -X PATCH "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Updated Name"}' \
  -s | jq '.data'
echo

echo "📋 AFTER PATCH - Check if others preserved:"
curl -X GET "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq '.data'
echo

# Reset again
curl -X PUT "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Original Name", "date_of_birth": "1990-01-01", "address": "Original Address", "avatar_url": "https://example.com/original.jpg"}' \
  -s > /dev/null

echo "🧪 TEST 2: PATCH with full_name + explicit nulls (WILL clear others)"
curl -X PATCH "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Updated Name", "date_of_birth": null, "address": null}' \
  -s | jq '.data'
echo

echo "📋 AFTER PATCH with nulls - Check if others cleared:"
curl -X GET "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq '.data'
echo

echo "=== CONCLUSION ==="
echo "If your PATCH requests are clearing other fields, your frontend is sending explicit null values!"
echo "✅ Correct: PATCH with only fields you want to update"
echo "❌ Wrong: PATCH with null values for fields you don't want to update"
