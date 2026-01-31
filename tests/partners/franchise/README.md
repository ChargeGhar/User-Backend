# Franchise Partner Payout - Full Lifecycle Test

## Overview

Comprehensive end-to-end test for the franchise partner payout system with real-time database state tracking at each step.

## Test Coverage

### Complete Flow
1. **Revenue Creation** - Create 3 rental transactions (100, 150, 200 NPR)
2. **Revenue Distribution** - Distribute to franchise and vendor
3. **Vendor Payout** - Complete vendor payout flow (20 NPR)
4. **Franchise Payout** - Complete franchise payout flow (50 NPR)
5. **Verification** - Verify final balances match expectations

### Database State Tracking

The test shows real-time database state after each action:
- Partner balances (balance & total_earnings)
- Revenue distribution counts (total, distributed, pending)
- Payout status counts (PENDING, APPROVED, PROCESSING, COMPLETED, REJECTED)

## Running the Test

### Inside Docker Container
```bash
cd /mnt/e/Companies/DEVALAYA/Deva_ChargeGhar/ChargeGhar
docker compose exec api uv run python tests/partners/franchise/test_full_lifecycle.py
```

### Direct Execution
```bash
cd ChargeGhar
python tests/partners/franchise/test_full_lifecycle.py
```

## Expected Results

### Final Balances
- **Franchise (FR-001)**
  - balance: 86.83 NPR
  - total_earnings: 156.83 NPR

- **Vendor (VN-003)**
  - balance: 7.68 NPR
  - total_earnings: 27.68 NPR

### Transaction Flow
```
1. Revenue: 450 NPR (3 transactions)
   → Franchise: +156.83, Vendor: +27.68

2. Vendor Payout: -20 NPR
   → Franchise: 156.83 → 136.83 (deducted)
   → Vendor: 27.68 → 7.68 (deducted)

3. Franchise Payout: -50 NPR
   → Franchise: 136.83 → 86.83 (deducted)
   → Vendor: 7.68 (unchanged)
```

## Test Steps Detail

### Step 0: Cleanup
- Deletes all revenue distributions for test partners
- Rejects all pending payouts
- Resets balances to 0

### Step 1: Create Revenue Transactions
- Creates 3 completed rentals with payments
- Creates revenue distribution records
- **No balance changes yet** (not distributed)

### Step 2: Distribute Revenue
- Marks revenue as distributed
- Updates franchise balance: 0 → 156.83
- Updates vendor balance: 0 → 27.68
- Updates total_earnings for both

### Step 3: Vendor Payout Flow
1. **Create Request** (20 NPR)
   - Status: PENDING
   - No balance changes

2. **Franchise Approves**
   - Status: PENDING → APPROVED
   - No balance changes

3. **Franchise Completes**
   - Status: APPROVED → COMPLETED
   - Franchise balance: 156.83 → 136.83
   - Vendor balance: 27.68 → 7.68
   - total_earnings: unchanged

### Step 4: Franchise Payout Flow
1. **Create Request** (50 NPR)
   - Status: PENDING
   - No balance changes

2. **Admin Approves**
   - Status: PENDING → APPROVED
   - No balance changes

3. **Admin Processes**
   - Status: APPROVED → PROCESSING
   - No balance changes

4. **Admin Completes**
   - Status: PROCESSING → COMPLETED
   - Franchise balance: 136.83 → 86.83
   - total_earnings: unchanged

### Step 5: Verification
- Verifies all final balances match expectations
- Checks both balance and total_earnings

## Business Rules Verified

- ✅ **BR8.1**: ChargeGhar pays Franchises
- ✅ **BR8.3**: Franchise pays Vendors
- ✅ **BR8.5**: Dual balance deduction (vendor payout affects both)
- ✅ **BR10.2**: Franchise controls own vendors
- ✅ **BR12.2**: Franchise views own data

## Key Findings

### Balance Tracking
- **balance**: Current available funds (changes with revenue, payout, reversal)
- **total_earnings**: Lifetime earnings (changes with revenue, reversal only)
- Payouts reduce balance only ✅
- Reversals reduce both ✅

### Payout Workflows
- **Vendor Payout**: PENDING → APPROVED → COMPLETED (2 steps)
- **Franchise Payout**: PENDING → APPROVED → PROCESSING → COMPLETED (3 steps)

### Dual Deduction
- Vendor payouts deduct from BOTH franchise and vendor balances
- Franchise payouts deduct from franchise balance only

## Color Coding

- 🟦 **Blue**: Informational messages
- 🟩 **Green**: Success messages
- 🟥 **Red**: Error messages
- 🟨 **Yellow**: Database state sections
- 🟪 **Purple**: Headers and steps

## Exit Codes

- `0`: All tests passed
- `1`: Tests failed or exception occurred

## Troubleshooting

### Import Errors
If you see `ImportError: cannot import name 'AdminPartnerService'`:
- The service exists at `api/admin/services/admin_partner_service.py`
- Import directly: `from api.admin.services.admin_partner_service import AdminPartnerService`

### Duplicate Key Errors
If you see `duplicate key value violates unique constraint "rentals_rental_code_key"`:
- The test uses unique rental codes with UUID
- This should not happen in normal execution

### Balance Mismatch
If final balances don't match:
- Check if there are existing payouts/revenues from previous tests
- Run cleanup step manually
- Check for concurrent modifications

## Future Enhancements

- [ ] Add reversal scenario testing
- [ ] Add edge case testing (insufficient balance, duplicate requests)
- [ ] Add concurrent payout testing
- [ ] Add performance benchmarks
- [ ] Add API endpoint testing (currently tests services directly)
