#!/bin/bash
# =============================================================
# test_multi_user_same_device.sh
# Tests that multiple users can independently use the same
# physical device (shared/handed-over phone scenario).
#
# Two test modes:
#   1. HTTP API test  — exercises the real HTTP path end-to-end
#   2. Service layer  — calls service/repo directly (no PgBouncer)
#      and asserts DB state precisely.
# =============================================================
# Run from INSIDE the container:
#   docker compose exec api bash /application/api/user/auth/tests/test_multi_user_same_device.sh
# =============================================================

set -euo pipefail

BASE_URL="http://localhost:80"
DEVICE_ID="shared-test-phone-$(date +%s)"
PASS=0
FAIL=0

h1()  { echo ""; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; echo "🧪  $*"; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }
ok()  { echo "  ✅  $*"; PASS=$((PASS+1)); }
fail(){ echo "  ❌  $*"; FAIL=$((FAIL+1)); }
info(){ echo "  ℹ️   $*"; }

assert_true() {
    local val
    val=$(echo "$1" | jq "$2" 2>/dev/null || echo "false")
    if [ "$val" = "true" ]; then ok "$3"; else fail "$3 (got: $val)"; fi
}

# Pipe-based python shell — variables expand correctly
pyshell() {
    cd /application
    echo "$1" | python manage.py shell 2>/dev/null \
      | grep -E -v '^(20[0-9]{2}|[[:space:]]*(DEBUG|WARNING|INFO|[0-9]+ objects))' \
      | grep -v '^\s*$' \
      || true
}

# Register a brand-new user end-to-end, return "ACCESS_TOKEN USER_ID"
register_user() {
    local email="$1" username="$2"

    curl -s -X POST "$BASE_URL/api/auth/otp/request" \
        -H "Content-Type: application/json" \
        -d "{\"identifier\": \"$email\"}" > /dev/null

    local otp
    otp=$(pyshell "
from django.core.cache import cache
data = cache.get('unified_otp:$email')
print(data['otp'] if data else 'NOT_FOUND')
" | tail -1)
    [ "$otp" = "NOT_FOUND" ] && { echo "OTP_FAIL"; return 1; }

    local vtoken
    vtoken=$(curl -s -X POST "$BASE_URL/api/auth/otp/verify" \
        -H "Content-Type: application/json" \
        -d "{\"identifier\": \"$email\", \"otp\": \"$otp\"}" \
        | jq -r '.data.verification_token')

    local resp
    resp=$(curl -s -X POST "$BASE_URL/api/auth/complete" \
        -H "Content-Type: application/json" \
        -d "{\"identifier\": \"$email\", \"verification_token\": \"$vtoken\", \"username\": \"$username\"}")

    local access uid
    access=$(echo "$resp" | jq -r '.data.tokens.access')
    uid=$(echo "$resp" | jq -r '.data.user.id')
    echo "$access $uid"
}

# ══════════════════════════════════════════════════════════════
h1 "PART A — Direct service-layer integration test"
# ══════════════════════════════════════════════════════════════
# This bypasses PgBouncer and HTTP layers, calling the service
# and repo directly in the same process, with a fresh DB connection.
# This is the most reliable way to assert DB state.

SVC_RESULT=$(pyshell "
import uuid, sys
from api.user.auth.models import UserDevice, User
from api.user.auth.services.user_device_service import UserDeviceService

# Create two minimal in-memory users
try:
    u1 = User.objects.create(email='svc_test_a@x.local', username='svc_a_test', is_active=True, status='ACTIVE')
    u2 = User.objects.create(email='svc_test_b@x.local', username='svc_b_test', is_active=True, status='ACTIVE')
    dev_id = 'svctest-' + uuid.uuid4().hex[:8]
    svc = UserDeviceService()

    # u1 registers device
    svc.register_device(u1, {'device_id': dev_id, 'fcm_token': 'fcm-svc-a', 'device_type': 'ANDROID'})
    after_u1 = list(UserDevice.objects.filter(device_id=dev_id).values('user_id', 'is_active'))
    u1_active = [r for r in after_u1 if r['user_id'] == u1.id and r['is_active']]
    print('SVC_STEP1_OK' if u1_active else 'SVC_STEP1_FAIL')

    # u2 registers same device (no IntegrityError expected)
    svc.register_device(u2, {'device_id': dev_id, 'fcm_token': 'fcm-svc-b', 'device_type': 'ANDROID'})
    after_u2 = list(UserDevice.objects.filter(device_id=dev_id).values('user_id', 'is_active'))

    u1_deactivated = [r for r in after_u2 if r['user_id'] == u1.id and not r['is_active']]
    u2_active       = [r for r in after_u2 if r['user_id'] == u2.id and r['is_active']]
    print('SVC_STEP2_OK' if (u1_deactivated and u2_active) else f'SVC_STEP2_FAIL: {after_u2}')

    # u1 re-registers (takes device back)
    svc.register_device(u1, {'device_id': dev_id, 'fcm_token': 'fcm-svc-a-v2', 'device_type': 'ANDROID'})
    after_u1v2 = list(UserDevice.objects.filter(device_id=dev_id).values('user_id', 'is_active', 'fcm_token'))
    u2_now_inactive = [r for r in after_u1v2 if r['user_id'] == u2.id and not r['is_active']]
    u1_now_active   = [r for r in after_u1v2 if r['user_id'] == u1.id and r['is_active'] and r['fcm_token'] == 'fcm-svc-a-v2']
    print('SVC_STEP3_OK' if (u2_now_inactive and u1_now_active) else f'SVC_STEP3_FAIL: {after_u1v2}')

except Exception as e:
    print(f'SVC_EXCEPTION: {e}')
finally:
    UserDevice.objects.filter(device_id=dev_id).delete() if 'dev_id' in dir() else None
    try: u1.delete()
    except: pass
    try: u2.delete()
    except: pass
    print('SVC_CLEANUP_DONE')
")

echo "$SVC_RESULT"
echo "$SVC_RESULT" | grep -q "SVC_STEP1_OK" && ok "Service: User A device registration creates active row" || fail "Service: User A device registration failed"
echo "$SVC_RESULT" | grep -q "SVC_STEP2_OK" && ok "Service: User B on same device evicts User A (is_active=False) and User B is active" || fail "Service: Eviction failed — both rows still active"
echo "$SVC_RESULT" | grep -q "SVC_STEP3_OK" && ok "Service: User A re-registers device, evicts User B and becomes active again" || fail "Service: Device hand-back failed"
echo "$SVC_RESULT" | grep -q "SVC_CLEANUP_DONE" && ok "Service: Cleanup completed" || fail "Service: Cleanup error"

# ══════════════════════════════════════════════════════════════
h1 "PART B — HTTP API end-to-end test"
# ══════════════════════════════════════════════════════════════

TS=$(date +%s)
EMAIL_A="shared.device.a.${TS}@example.com"; NAME_A="SharedDevA${TS: -4}"
EMAIL_B="shared.device.b.${TS}@example.com"; NAME_B="SharedDevB${TS: -4}"

info "Device ID : $DEVICE_ID"
info "User A    : $EMAIL_A"
info "User B    : $EMAIL_B"

READ_A=$(register_user "$EMAIL_A" "$NAME_A")
ACCESS_A=$(echo "$READ_A" | cut -d' ' -f1)
USER_A_ID=$(echo "$READ_A" | cut -d' ' -f2)
[ -n "$ACCESS_A" ] && [ "$ACCESS_A" != "null" ] && ok "User A registered (id=$USER_A_ID)" || { fail "User A registration failed"; exit 1; }

pyshell "from django.core.cache import cache; [cache.delete(k) for k in (cache.keys('rate_limit:*') or [])]" > /dev/null

READ_B=$(register_user "$EMAIL_B" "$NAME_B")
ACCESS_B=$(echo "$READ_B" | cut -d' ' -f1)
USER_B_ID=$(echo "$READ_B" | cut -d' ' -f2)
[ -n "$ACCESS_B" ] && [ "$ACCESS_B" != "null" ] && ok "User B registered (id=$USER_B_ID)" || { fail "User B registration failed"; exit 1; }
info "User A id=$USER_A_ID  |  User B id=$USER_B_ID"

# ── STEP B1: User A registers device ────────────────────────
h1 "STEP B1 — User A registers the shared device"
REG_A=$(curl -s -X POST "$BASE_URL/api/auth/device" \
    -H "Authorization: Bearer $ACCESS_A" \
    -H "Content-Type: application/json" \
    -d "{\"device_id\": \"$DEVICE_ID\", \"fcm_token\": \"fcm-token-user-a\", \"device_type\": \"ANDROID\", \"device_name\": \"Shared Phone\"}")
echo "$REG_A" | jq .
assert_true "$REG_A" '.success' "User A device registration returned success"
A_DEV_UUID=$(echo "$REG_A" | jq -r '.data.id')
info "User A device DB uuid: $A_DEV_UUID"

# ── STEP B2: User B registers the SAME device ───────────────
h1 "STEP B2 — User B registers the SAME physical device (no IntegrityError)"
REG_B=$(curl -s -X POST "$BASE_URL/api/auth/device" \
    -H "Authorization: Bearer $ACCESS_B" \
    -H "Content-Type: application/json" \
    -d "{\"device_id\": \"$DEVICE_ID\", \"fcm_token\": \"fcm-token-user-b\", \"device_type\": \"ANDROID\", \"device_name\": \"Shared Phone\"}")
echo "$REG_B" | jq .
assert_true "$REG_B" '.success' "User B device registration succeeded (no 500 / IntegrityError)"
# Verify User B got a DIFFERENT DB record (they are a different user)
B_DEV_UUID=$(echo "$REG_B" | jq -r '.data.id')
info "User B device DB uuid: $B_DEV_UUID"
[ "$A_DEV_UUID" != "$B_DEV_UUID" ] && ok "User A and B have distinct device rows (correct)" || fail "Same device row re-used for different user (unexpected)"

# ── STEP B3: User A's JWT tokens still work ─────────────────
h1 "STEP B3 — Both users' JWT tokens work independently"
ME_A=$(curl -s -X GET "$BASE_URL/api/auth/me" -H "Authorization: Bearer $ACCESS_A")
A_ID_CHECK=$(echo "$ME_A" | jq -r '.data.id // empty')
[ "$A_ID_CHECK" = "$USER_A_ID" ] && ok "User A token: /api/auth/me returns User A's profile" || { echo "$ME_A" | jq .; fail "User A token rejected or wrong profile returned"; }

ME_B=$(curl -s -X GET "$BASE_URL/api/auth/me" -H "Authorization: Bearer $ACCESS_B")
B_ID_CHECK=$(echo "$ME_B" | jq -r '.data.id // empty')
[ "$B_ID_CHECK" = "$USER_B_ID" ] && ok "User B token: /api/auth/me returns User B's profile" || { echo "$ME_B" | jq .; fail "User B token rejected or wrong profile returned"; }

# ── STEP B4: User A re-registers (device hand-back) ─────────
h1 "STEP B4 — User A re-registers device (simulates taking phone back)"
REG_A2=$(curl -s -X POST "$BASE_URL/api/auth/device" \
    -H "Authorization: Bearer $ACCESS_A" \
    -H "Content-Type: application/json" \
    -d "{\"device_id\": \"$DEVICE_ID\", \"fcm_token\": \"fcm-token-user-a-updated\", \"device_type\": \"ANDROID\", \"device_name\": \"Shared Phone\"}")
echo "$REG_A2" | jq .
assert_true "$REG_A2" '.success' "User A re-registers same device successfully"
# Should return User A's SAME row UUID (updating it, not creating new)
A2_DEV_UUID=$(echo "$REG_A2" | jq -r '.data.id')
[ "$A2_DEV_UUID" = "$A_DEV_UUID" ] && ok "User A's row UUID is preserved on re-register (correct update_or_create)" || fail "Expected same UUID $A_DEV_UUID got $A2_DEV_UUID"
A2_FCM=$(echo "$REG_A2" | jq -r '.data.fcm_token')
[ "$A2_FCM" = "fcm-token-user-a-updated" ] && ok "FCM token updated for User A on re-register" || fail "FCM token not updated (got $A2_FCM)"

# ── Teardown ─────────────────────────────────────────────────
h1 "Teardown"
pyshell "
from api.user.auth.models import UserDevice
c, _ = UserDevice.objects.filter(device_id='$DEVICE_ID').delete()
print(f'Deleted {c} device rows')
" | tail -1

# ══════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "📊  MULTI-USER SAME DEVICE TEST SUMMARY"
echo "══════════════════════════════════════════"
echo "  ✅  Passed: $PASS"
echo "  ❌  Failed: $FAIL"
echo "══════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
    echo "🎉  All multi-user same device tests PASSED!"
    exit 0
else
    echo "💥  $FAIL test(s) FAILED"
    exit 1
fi
