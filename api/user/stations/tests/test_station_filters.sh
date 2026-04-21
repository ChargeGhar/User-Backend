#!/bin/bash
# =============================================================
# test_station_filters.sh
# Tests for GET /api/stations with max_distance and status filters
# =============================================================
# Run from INSIDE the container:
#   docker compose exec api bash /application/api/user/stations/tests/test_station_filters.sh
# OR from host with working directory = project root:
#   docker compose exec api bash api/user/stations/tests/test_station_filters.sh
# =============================================================

set -euo pipefail

BASE_URL="http://localhost:80"   # inside container, gunicorn listens on 80
PASS=0
FAIL=0

# ── Helpers ────────────────────────────────────────────────────
h1()  { echo ""; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; echo "🧪  $*"; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }
ok()  { echo "  ✅  $*"; PASS=$((PASS+1)); }
fail(){ echo "  ❌  $*"; FAIL=$((FAIL+1)); }
info(){ echo "  ℹ️   $*"; }

assert_true() {
    local val
    val=$(echo "$1" | jq "$2" 2>/dev/null || echo "false")
    if [ "$val" = "true" ]; then ok "$3"; else fail "$3 (got: $val)"; fi
}

# Django shell helper — runs python snippet, strips Django log noise
dshell() {
    cd /application
    python manage.py shell -c "$1" 2>/dev/null \
      | grep -v '^\s*$' \
      | grep -v DEBUG \
      | grep -v WARNING \
      | grep -v INFO \
      | grep -v 'objects imported' \
      || true
}

# ── Seed: create one OFFLINE station ──────────────────────────
h1 "Setup — seeding OFFLINE test station"

SEED_RESULT=$(dshell "
from api.user.stations.models import Station
station, created = Station.objects.get_or_create(
    serial_number='TEST_OFFLINE_01',
    defaults=dict(
        station_name='Test Offline Station',
        imei='999999999999901',
        latitude=27.7172,
        longitude=85.3240,
        address='Test Address, Kathmandu',
        total_slots=2,
        status='OFFLINE',
        is_maintenance=False,
        is_deleted=False,
    )
)
print('CREATED' if created else 'ALREADY_EXISTS')
" | tail -1)

OFFLINE_SN="TEST_OFFLINE_01"
info "Offline station seed: $SEED_RESULT"

# ── TEST 1: No filters ─────────────────────────────────────────
h1 "Test 1 — GET /api/stations (no filters)"

R=$(curl -s "$BASE_URL/api/stations")
echo "$R" | jq .
assert_true "$R" '.success' "Response success=true"
assert_true "$R" '.data.results | length > 0' "Results list is non-empty"

# ── TEST 2: status=ONLINE ──────────────────────────────────────
h1 "Test 2 — GET /api/stations?status=ONLINE"

R=$(curl -s "$BASE_URL/api/stations?status=ONLINE")
echo "$R" | jq .
assert_true "$R" '.success' "Response success=true"

OFFLINE_COUNT=$(echo "$R" | jq '[.data.results[] | select(.status=="OFFLINE")] | length')
if [ "$OFFLINE_COUNT" -eq 0 ]; then
    ok "No OFFLINE stations returned when status=ONLINE"
else
    fail "Found $OFFLINE_COUNT OFFLINE station(s) in ONLINE-filtered results"
fi
assert_true "$R" '.data.results | length > 0' "At least 1 ONLINE station returned"

# ── TEST 3: status=OFFLINE ─────────────────────────────────────
h1 "Test 3 — GET /api/stations?status=OFFLINE"

R=$(curl -s "$BASE_URL/api/stations?status=OFFLINE")
echo "$R" | jq .
assert_true "$R" '.success' "Response success=true"

ONLINE_COUNT=$(echo "$R" | jq '[.data.results[] | select(.status=="ONLINE")] | length')
if [ "$ONLINE_COUNT" -eq 0 ]; then
    ok "No ONLINE stations returned when status=OFFLINE"
else
    fail "Found $ONLINE_COUNT ONLINE station(s) in OFFLINE-filtered results"
fi

HAS_OFFLINE=$(echo "$R" | jq --arg sn "$OFFLINE_SN" '[.data.results[] | select(.serial_number==$sn)] | length')
if [ "$HAS_OFFLINE" -ge 1 ]; then
    ok "Seeded OFFLINE station ($OFFLINE_SN) appears in results"
else
    fail "Seeded OFFLINE station ($OFFLINE_SN) missing from results"
fi

# ── TEST 4: lowercase status normalisation ─────────────────────
h1 "Test 4 — status=online (lowercase → normalised to ONLINE)"

R=$(curl -s "$BASE_URL/api/stations?status=online")
echo "$R" | jq .
assert_true "$R" '.success' "Response accepted (lowercase status)"
OFFLINE_COUNT2=$(echo "$R" | jq '[.data.results[] | select(.status=="OFFLINE")] | length')
if [ "$OFFLINE_COUNT2" -eq 0 ]; then
    ok "Lowercase 'online' normalised — no OFFLINE leaked"
else
    fail "Lowercase normalisation broken — got $OFFLINE_COUNT2 OFFLINE results"
fi

# ── TEST 5: Distance 1km (KTM area) ───────────────────────────
h1 "Test 5 — GET /api/stations?lat=27.7172&lng=85.3240&max_distance=1"

R=$(curl -s "$BASE_URL/api/stations?lat=27.7172&lng=85.3240&max_distance=1")
echo "$R" | jq .
assert_true "$R" '.success' "Response success=true"
assert_true "$R" '.data.results | length > 0' "At least 1 station within 1km"

POKHARA_COUNT=$(echo "$R" | jq '[.data.results[] | select(.serial_number=="PKR001")] | length')
if [ "$POKHARA_COUNT" -eq 0 ]; then
    ok "Pokhara station (130+km away) excluded from 1km radius"
else
    fail "Pokhara station unexpectedly appeared in 1km results"
fi

# ── TEST 6: Distance 50km ──────────────────────────────────────
h1 "Test 6 — GET /api/stations?lat=27.7&lng=85.3&max_distance=50&status=ONLINE"

R=$(curl -s "$BASE_URL/api/stations?lat=27.7&lng=85.3&max_distance=50&status=ONLINE")
echo "$R" | jq .
assert_true "$R" '.success' "Response success=true"
COUNT=$(echo "$R" | jq '.data.results | length')
info "Stations within 50km (ONLINE): $COUNT"
assert_true "$R" '.data.results | length > 0' "Stations found within 50km"

# ── TEST 7: max_distance=999 capped gracefully ─────────────────
h1 "Test 7 — max_distance=999 (server caps at 50km, no 500)"

R=$(curl -s "$BASE_URL/api/stations?lat=27.7&lng=85.3&max_distance=999")
echo "$R" | jq .
assert_true "$R" '.success' "Request accepted gracefully (not rejected)"

# ── TEST 8: max_distance=abc → 400 ────────────────────────────
h1 "Test 8 — max_distance=abc (invalid float) → error response"

R=$(curl -s "$BASE_URL/api/stations?lat=27.7&lng=85.3&max_distance=abc")
echo "$R" | jq .
assert_true "$R" '.success | not' "success=false for non-numeric max_distance"

# ── TEST 9: Combined status + distance ────────────────────────
h1 "Test 9 — status=ONLINE + lat/lng + max_distance=5"

R=$(curl -s "$BASE_URL/api/stations?status=ONLINE&lat=27.7172&lng=85.3240&max_distance=5")
echo "$R" | jq .
assert_true "$R" '.success' "Response success=true"

OFFLINE_COMBO=$(echo "$R" | jq '[.data.results[] | select(.status=="OFFLINE")] | length')
if [ "$OFFLINE_COMBO" -eq 0 ]; then
    ok "Combined filter: no OFFLINE stations leaked"
else
    fail "Combined filter: $OFFLINE_COMBO OFFLINE station(s) leaked"
fi

# ── Teardown ──────────────────────────────────────────────────
h1 "Teardown — removing seeded OFFLINE test station"

dshell "
from api.user.stations.models import Station
count, _ = Station.objects.filter(serial_number='TEST_OFFLINE_01').delete()
print(f'Deleted {count} station(s)')
"
info "Test station removed"

# ── Summary ───────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo "📊  STATION FILTER TESTS SUMMARY"
echo "══════════════════════════════════════════"
echo "  ✅  Passed: $PASS"
echo "  ❌  Failed: $FAIL"
echo "══════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
    echo "🎉  All station filter tests PASSED!"
    exit 0
else
    echo "💥  $FAIL test(s) FAILED — check output above"
    exit 1
fi
