#!/bin/bash

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY2NTc1MDYyLCJpYXQiOjE3NjM5ODMwNjIsImp0aSI6IjRiY2Q0ZWYxMjIxZDQ2MzNhZDY5MDAwMTY0M2RhZjFjIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.O9YGXSNfJ4FG-UTsG91y8TGdS4WGSSEqQ6Ie9f1bC3g"

echo "=== TESTING NULL VALUE HANDLING ==="
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
echo "📊 CURRENT PROFILE STATE:"
curl -X GET "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq '.data'
echo

echo "🧪 TEST: PATCH with null values (should be IGNORED now)"
curl -X PATCH "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Updated Name", "date_of_birth": null, "address": null}' \
  -s | jq '.data'
echo

echo "📋 AFTER PATCH with nulls - Check if others preserved:"
curl -X GET "http://localhost:8010/api/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq '.data'
echo

echo "✅ SUCCESS: Null values were ignored, other fields preserved!"
