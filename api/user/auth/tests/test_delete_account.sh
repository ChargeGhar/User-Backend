#!/bin/bash
# =============================================================
# test_delete_account.sh
# Tests for DELETE /api/auth/account — soft-delete, no cascade
# =============================================================
# Run from INSIDE the container:
#   docker compose exec api bash /application/api/user/auth/tests/test_delete_account.sh
# =============================================================

set -euo pipefail

BASE_URL="http://localhost:80"
TEST_EMAIL="test.softdelete.$(date +%s)@example.com"
TEST_USERNAME="SoftDelUser$(date +%s | tail -c 5)"
PASS=0
FAIL=0

# ── Helpers ─────────────────────────────────────────────────────
h1()  { echo ""; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; echo "🧪  $*"; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }
ok()  { echo "  ✅  $*"; PASS=$((PASS+1)); }
fail(){ echo "  ❌  $*"; FAIL=$((FAIL+1)); }
info(){ echo "  ℹ️   $*"; }

assert_true() {
    local val
    val=$(echo "$1" | jq "$2" 2>/dev/null || echo "false")
    if [ "$val" = "true" ]; then ok "$3"; else fail "$3 (got: $val)"; fi
}

# Django shell — NOTE: uses double-quotes so $VAR expands inside the snippet
pyshell() {
    # pyshell "<python code with $VARS already expanded by caller>"
    cd /application
    echo "$1" | python manage.py shell 2>/dev/null \
      | grep -v '^\s*$' \
      | grep -E -v '^(20[0-9]{2}|[[:space:]]*(DEBUG|WARNING|INFO|[0-9]+ objects))' \
      || true
}

# ══════════════════════════════════════════════════════════════
h1 "STEP 1 — Register fresh user via OTP flow"
# ══════════════════════════════════════════════════════════════
info "Email   : $TEST_EMAIL"
info "Username: $TEST_USERNAME"

## 1a. Request OTP
OTP_RESP=$(curl -s -X POST "$BASE_URL/api/auth/otp/request" \
    -H "Content-Type: application/json" \
    -d "{\"identifier\": \"$TEST_EMAIL\"}")
echo "$OTP_RESP" | jq .
assert_true "$OTP_RESP" '.success' "OTP request succeeded"

## 1b. Read OTP via shell  (pyshell with double-quote expansion)
OTP=$(pyshell "
from django.core.cache import cache
data = cache.get('unified_otp:$TEST_EMAIL')
print(data['otp'] if data else 'NOT_FOUND')
" | tail -1)

if [ "$OTP" = "NOT_FOUND" ] || [ -z "$OTP" ]; then
    fail "OTP not found in Redis — aborting test"
    exit 1
fi
ok "OTP from Redis: $OTP"

## 1c. Verify OTP
VERIFY_RESP=$(curl -s -X POST "$BASE_URL/api/auth/otp/verify" \
    -H "Content-Type: application/json" \
    -d "{\"identifier\": \"$TEST_EMAIL\", \"otp\": \"$OTP\"}")
echo "$VERIFY_RESP" | jq .
assert_true "$VERIFY_RESP" '.success' "OTP verify succeeded"

VTOKEN=$(echo "$VERIFY_RESP" | jq -r '.data.verification_token')
info "Vtoken: ${VTOKEN:0:30}..."

## 1d. Complete registration
COMPLETE_RESP=$(curl -s -X POST "$BASE_URL/api/auth/complete" \
    -H "Content-Type: application/json" \
    -d "{\"identifier\": \"$TEST_EMAIL\", \"verification_token\": \"$VTOKEN\", \"username\": \"$TEST_USERNAME\"}")
echo "$COMPLETE_RESP" | jq .
assert_true "$COMPLETE_RESP" '.success' "Registration completed"

ACCESS_TOKEN=$(echo "$COMPLETE_RESP" | jq -r '.data.tokens.access')
REFRESH_TOKEN=$(echo "$COMPLETE_RESP" | jq -r '.data.tokens.refresh')
USER_ID=$(echo "$COMPLETE_RESP" | jq -r '.data.user.id')
info "User ID : $USER_ID"
info "Access  : ${ACCESS_TOKEN:0:50}..."

if [ "$USER_ID" = "null" ] || [ -z "$USER_ID" ]; then
    fail "No user_id — aborting"
    exit 1
fi

# ══════════════════════════════════════════════════════════════
h1 "STEP 2 — Verify auto-created account records"
# ══════════════════════════════════════════════════════════════

PROFILE_OK=$(pyshell "
from api.user.auth.models import UserProfile
print('YES' if UserProfile.objects.filter(user_id=$USER_ID).exists() else 'NO')
" | tail -1)
[ "$PROFILE_OK" = "YES" ] && ok "UserProfile auto-created" || fail "UserProfile missing"

WALLET_OK=$(pyshell "
from api.user.payments.models import Wallet
print('YES' if Wallet.objects.filter(user_id=$USER_ID).exists() else 'NO')
" | tail -1)
[ "$WALLET_OK" = "YES" ] && ok "Wallet auto-created" || fail "Wallet missing"

POINTS_OK=$(pyshell "
from api.user.points.models import UserPoints
print('YES' if UserPoints.objects.filter(user_id=$USER_ID).exists() else 'NO')
" | tail -1)
[ "$POINTS_OK" = "YES" ] && ok "UserPoints auto-created" || fail "UserPoints missing"

# ══════════════════════════════════════════════════════════════
h1 "STEP 3 — Seed Transaction + UserDevice"
# ══════════════════════════════════════════════════════════════

TXN_SEED=$(pyshell "
import uuid
from api.user.payments.models import Transaction
txn = Transaction.objects.create(
    user_id=$USER_ID,
    transaction_id='TEST-TXN-' + uuid.uuid4().hex[:8].upper(),
    transaction_type='TOPUP',
    amount='100.00',
    currency='NPR',
    status='SUCCESS',
    payment_method_type='WALLET',
)
print('OK:' + str(txn.id))
" | tail -1)

if echo "$TXN_SEED" | grep -q "^OK:"; then
    TXN_ID="${TXN_SEED#OK:}"
    ok "Transaction seeded (id=$TXN_ID)"
else
    fail "Transaction seed failed: $TXN_SEED"
    TXN_ID=""
fi

DEV_SEED=$(pyshell "
from api.user.auth.models import UserDevice, User
u = User.objects.get(id=$USER_ID)
dev = UserDevice.objects.create(
    user=u,
    device_id='test-device-${USER_ID}',
    fcm_token='test-fcm-${USER_ID}',
    device_type='ANDROID',
    device_name='Test Phone',
    is_active=True,
)
print('OK:' + str(dev.id))
" | tail -1)

if echo "$DEV_SEED" | grep -q "^OK:"; then
    ok "UserDevice seeded"
else
    fail "UserDevice seed failed: $DEV_SEED"
fi

# ══════════════════════════════════════════════════════════════
h1 "STEP 4 — DELETE /api/auth/account"
# ══════════════════════════════════════════════════════════════

DELETE_RESP=$(curl -s -X DELETE "$BASE_URL/api/auth/account" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
echo "$DELETE_RESP" | jq .
assert_true "$DELETE_RESP" '.success' "Delete account response success=true"

# ══════════════════════════════════════════════════════════════
h1 "STEP 5 — User row still exists but anonymized"
# ══════════════════════════════════════════════════════════════

USER_STATE=$(pyshell "
from api.user.auth.models import User
try:
    u = User.objects.get(id=$USER_ID)
    print('EXISTS')
    print('is_active=' + str(u.is_active))
    print('status=' + u.status)
    print('email_placeholder=' + str(u.email.startswith('deleted_')))
    print('phone_null=' + str(u.phone_number is None))
    print('username_placeholder=' + str(u.username.startswith('deleted_')))
except User.DoesNotExist:
    print('HARD_DELETED')
")

echo "$USER_STATE"

if echo "$USER_STATE" | grep -q "HARD_DELETED"; then
    fail "User was HARD DELETED — cascade still present!"
else
    echo "$USER_STATE" | grep -q "is_active=False"           && ok "is_active=False"          || fail "is_active not False"
    echo "$USER_STATE" | grep -q "status=INACTIVE"           && ok "status=INACTIVE"           || fail "status not INACTIVE"
    echo "$USER_STATE" | grep -q "email_placeholder=True"    && ok "Email anonymized"          || fail "Email not anonymized"
    echo "$USER_STATE" | grep -q "phone_null=True"           && ok "Phone cleared to NULL"     || fail "Phone not cleared"
    echo "$USER_STATE" | grep -q "username_placeholder=True" && ok "Username anonymized"       || fail "Username not anonymized"
fi

# ══════════════════════════════════════════════════════════════
h1 "STEP 6 — Transaction record PRESERVED (no cascade wipe)"
# ══════════════════════════════════════════════════════════════

if [ -n "$TXN_ID" ]; then
    TXN_ALIVE=$(pyshell "
from api.user.payments.models import Transaction
print('YES' if Transaction.objects.filter(id='$TXN_ID').exists() else 'NO')
" | tail -1)
    [ "$TXN_ALIVE" = "YES" ] && ok "Transaction preserved ✔ (no CASCADE DELETE)" \
                               || fail "Transaction was CASCADE DELETED!"
else
    fail "Transaction ID not captured — skipping"
fi

# ══════════════════════════════════════════════════════════════
h1 "STEP 7 — UserDevice records DELETED (JWT invalidation)"
# ══════════════════════════════════════════════════════════════

DEV_GONE=$(pyshell "
from api.user.auth.models import UserDevice
print('YES' if UserDevice.objects.filter(user_id=$USER_ID).exists() else 'NO')
" | tail -1)
[ "$DEV_GONE" = "NO" ] && ok "All UserDevice rows deleted (sessions wiped)" \
                        || fail "UserDevice rows still exist — sessions NOT wiped"

# ══════════════════════════════════════════════════════════════
h1 "STEP 8 — JWT refresh REJECTED after deactivation"
# ══════════════════════════════════════════════════════════════

REFRESH_AFTER=$(curl -s -X POST "$BASE_URL/api/auth/refresh" \
    -H "Content-Type: application/json" \
    -d "{\"refresh\": \"$REFRESH_TOKEN\"}")
echo "$REFRESH_AFTER" | jq .
assert_true "$REFRESH_AFTER" '.success | not' "Refresh token rejected for inactive account"

# ══════════════════════════════════════════════════════════════
h1 "STEP 9 — Original email no longer resolves to any user"
# ══════════════════════════════════════════════════════════════

EMAIL_LOOKUP=$(pyshell "
from api.user.auth.repositories import UserRepository
r = UserRepository()
print('FOUND' if r.exists('$TEST_EMAIL') else 'NOT_FOUND')
" | tail -1)
[ "$EMAIL_LOOKUP" = "NOT_FOUND" ] \
    && ok "Email '$TEST_EMAIL' no longer in system (PII cleared)" \
    || fail "Email still resolves — PII not cleared"

# ══════════════════════════════════════════════════════════════
h1 "STEP 10 — Wallet + Points PRESERVED"
# ══════════════════════════════════════════════════════════════

WALLET_ALIVE=$(pyshell "
from api.user.payments.models import Wallet
print('YES' if Wallet.objects.filter(user_id=$USER_ID).exists() else 'NO')
" | tail -1)
[ "$WALLET_ALIVE" = "YES" ] && ok "Wallet preserved" || fail "Wallet CASCADE DELETED"

POINTS_ALIVE=$(pyshell "
from api.user.points.models import UserPoints
print('YES' if UserPoints.objects.filter(user_id=$USER_ID).exists() else 'NO')
" | tail -1)
[ "$POINTS_ALIVE" = "YES" ] && ok "UserPoints preserved" || fail "UserPoints CASCADE DELETED"

# ══════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "📊  DELETE ACCOUNT TEST SUMMARY"
echo "══════════════════════════════════════════"
echo "  ✅  Passed: $PASS"
echo "  ❌  Failed: $FAIL"
echo "══════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
    echo "🎉  All delete-account tests PASSED!"
    exit 0
else
    echo "💥  $FAIL test(s) FAILED — check output above"
    exit 1
fi
