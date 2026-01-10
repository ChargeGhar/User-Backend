#!/bin/bash

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY2NTc1MDYyLCJpYXQiOjE3NjM5ODMwNjIsImp0aSI6IjRiY2Q0ZWYxMjIxZDQ2MzNhZDY5MDAwMTY0M2RhZjFjIiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSAgICJ9.O9YGXSNfJ4FG-UTsG91y8TGdS4WGSSEqQ6Ie9f1bC3g"

echo "=== Testing Profile PUT and PATCH Endpoints ==="
echo "Token: ${TOKEN:0:50}..."
echo

# Test 1: GET current profile
echo "1. GET current profile:"
curl -X GET http://localhost:8010/api/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq '.'
echo

# Test 2: PATCH - Update only full_name
echo "2. PATCH - Update only full_name:"
curl -X PATCH http://localhost:8010/api/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -F "full_name=Janak Updated" \
  -s | jq '.'
echo

# Test 3: PATCH - Update only date_of_birth
echo "3. PATCH - Update only date_of_birth:"
curl -X PATCH http://localhost:8010/api/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -F "date_of_birth=1990-01-01" \
  -s | jq '.'
echo

# Test 4: PATCH - Update only address
echo "4. PATCH - Update only address:"
curl -X PATCH http://localhost:8010/api/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -F "address=Pokhara, Nepal" \
  -s | jq '.'
echo

# Test 5: PATCH - Update multiple fields (full_name + date_of_birth)
echo "5. PATCH - Update multiple fields (full_name + date_of_birth):"
curl -X PATCH http://localhost:8010/api/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -F "full_name=Janak Sharma" \
  -F "date_of_birth=1985-05-15" \
  -s | jq '.'
echo

# Test 6: PUT - Full update with all fields
echo "6. PUT - Full update with all fields:"
curl -X PUT http://localhost:8010/api/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -F "full_name=Janak Admin" \
  -F "date_of_birth=1990-01-01" \
  -F "address=Pokhara, Nepal" \
  -s | jq '.'
echo

# Test 7: PATCH - Update avatar_url
echo "7. PATCH - Update avatar_url:"
curl -X PATCH http://localhost:8010/api/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -F "avatar_url=https://example.com/avatar.jpg" \
  -s | jq '.'
echo

echo "=== Testing Complete ==="