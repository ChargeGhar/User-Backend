# Franchise Revenue & Payouts Implementation Plan

> **Phase:** 4 - Revenue & Payouts  
> **Status:** PLANNING  
> **Priority:** HIGH

---

## 1. Revenue Endpoint

### GET `/api/partner/franchise/revenue/`

**Purpose:** View own stations' transaction revenue

**Query Parameters:**
- `station_id` (UUID) - Filter by specific station
- `vendor_id` (UUID) - Filter by specific vendor
- `period` (string) - today|week|month|year|custom
- `start_date` (date) - Custom period start
- `end_date` (date) - Custom period end
- `page` (int) - Page number
- `page_size` (int) - Items per page

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "transaction_id": "uuid",
      "rental_id": "uuid",
      "station": {
        "id": "uuid",
        "station_name": "Chitwan Mall",
        "serial_number": "CTW001"
      },
      "vendor": {
        "id": "uuid",
        "code": "VN-003",
        "business_name": "Vendor Shop"
      },
      "gross_amount": "100.00",
      "vat_amount": "13.00",
      "service_charge": "2.50",
      "net_amount": "84.50",
      "chargeghar_share": "63.38",
      "franchise_share": "21.13",
      "vendor_share": "0.00",
      "is_distributed": true,
      "created_at": "2026-01-31T10:00:00Z"
    }
  ],
  "summary": {
    "total_transactions": 150,
    "total_gross": "15000.00",
    "total_net": "12675.00",
    "franchise_total_share": "3168.75"
  },
  "count": 150,
  "page": 1,
  "page_size": 20
}
```

**Business Rules:**
- BR12.2: Only own stations' transactions (franchise_id = franchise.id)
- Show all revenue_distributions for franchise's stations
- Include vendor info if vendor assigned

**Database Query:**
```sql
SELECT rd.*
FROM revenue_distributions rd
WHERE rd.franchise_id = {franchise_id}
  AND rd.is_reversal = FALSE
  AND (station_id = {station_id} OR {station_id} IS NULL)
  AND (vendor_id = {vendor_id} OR {vendor_id} IS NULL)
  AND rd.created_at >= {start_date}
  AND rd.created_at <= {end_date}
ORDER BY rd.created_at DESC
```

---

## 2. Payout Endpoints

### 2.1 GET `/api/partner/franchise/payouts/`

**Purpose:** View own payout history (from ChargeGhar)

**Query Parameters:**
- `status` - PENDING|APPROVED|PROCESSING|COMPLETED|REJECTED
- `page`, `page_size`

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "reference_id": "PO-FR-001-20260131",
      "payout_type": "CHARGEGHAR_TO_FRANCHISE",
      "amount": "10000.00",
      "net_amount": "10000.00",
      "status": "PENDING",
      "bank_name": "NIC Asia",
      "account_number": "1234567890",
      "account_holder_name": "Franchise Name",
      "created_at": "2026-01-31T10:00:00Z",
      "processed_at": null
    }
  ]
}
```

**Business Rules:**
- BR8.1: Franchise receives payouts from ChargeGhar
- Filter: `partner_id = franchise.id` AND `payout_type = CHARGEGHAR_TO_FRANCHISE`

---

### 2.2 POST `/api/partner/franchise/payouts/request/`

**Purpose:** Request payout from ChargeGhar

**Request:**
```json
{
  "amount": 10000.00,
  "bank_name": "NIC Asia",
  "account_number": "1234567890",
  "account_holder_name": "Franchise Name"
}
```

**Validations:**
1. Amount > 0
2. Amount <= franchise.balance
3. Bank details required
4. No pending payout exists

**Logic:**
1. Check franchise.balance >= amount
2. Create PayoutRequest with:
   - `partner_id = franchise.id`
   - `payout_type = CHARGEGHAR_TO_FRANCHISE` (auto-determined)
   - `status = PENDING`
   - Generate `reference_id = PO-FR-{code}-{timestamp}`
   - `net_amount = amount` (no deductions)
3. DO NOT deduct from balance yet (only when COMPLETED by admin)

**Business Rules:**
- BR8.1: ChargeGhar manages payouts to Franchises
- BR8.5: Franchise receives payout BEFORE paying vendors

---

### 2.3 GET `/api/partner/franchise/payouts/vendors/`

**Purpose:** View sub-vendor payout requests

**Query Parameters:**
- `status` - PENDING|APPROVED|PROCESSING|COMPLETED|REJECTED
- `vendor_id` (UUID)
- `page`, `page_size`

**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "reference_id": "PO-VN-003-20260131",
      "vendor": {
        "id": "uuid",
        "code": "VN-003",
        "business_name": "Vendor Shop",
        "balance": "5000.00"
      },
      "payout_type": "FRANCHISE_TO_VENDOR",
      "amount": "2000.00",
      "net_amount": "2000.00",
      "status": "PENDING",
      "bank_name": "Sunrise Bank",
      "created_at": "2026-01-31T10:00:00Z"
    }
  ]
}
```

**Business Rules:**
- BR8.3: Franchise manages payouts to Franchise-level Vendors
- Filter: `payout_type = FRANCHISE_TO_VENDOR` AND `partner.parent_id = franchise.id`

---

### 2.4 PATCH `/api/partner/franchise/payouts/vendors/{id}/approve/`

**Purpose:** Approve vendor payout request

**Request:**
```json
{
  "admin_notes": "Approved for processing"
}
```

**Logic:**
1. Verify payout belongs to franchise's vendor
2. Check status = PENDING
3. Update status = APPROVED
4. Set processed_by = franchise.user
5. Set processed_at = now()

**Business Rules:**
- BR8.3: Franchise approves vendor payouts
- Only PENDING payouts can be approved

---

### 2.5 PATCH `/api/partner/franchise/payouts/vendors/{id}/complete/`

**Purpose:** Complete vendor payout (mark as paid)

**Request:**
```json
{
  "admin_notes": "Payment transferred"
}
```

**Logic:**
1. Verify payout belongs to franchise's vendor
2. Check status IN (PENDING, APPROVED, PROCESSING)
3. Check franchise.balance >= payout.amount
4. **Deduct from vendor balance:** `vendor.balance -= payout.amount`
5. **Deduct from franchise balance:** `franchise.balance -= payout.amount`
6. Update status = COMPLETED
7. Set processed_by = franchise.user
8. Set processed_at = now()

**CRITICAL:**
- Vendor balance already has their share
- Franchise pays vendor from their own balance
- This is a balance transfer: Vendor → Franchise → ChargeGhar

**Business Rules:**
- BR8.3: Franchise pays vendors
- BR8.5: Franchise must have received payout from CG first

---

### 2.6 PATCH `/api/partner/franchise/payouts/vendors/{id}/reject/`

**Purpose:** Reject vendor payout request

**Request:**
```json
{
  "rejection_reason": "Insufficient documentation"
}
```

**Logic:**
1. Verify payout belongs to franchise's vendor
2. Check status = PENDING
3. Update status = REJECTED
4. Set rejection_reason
5. Set processed_by = franchise.user
6. Set processed_at = now()

---

## 3. Implementation Files

### Service: `franchise_payout_service.py`
```python
class FranchisePayoutService(BaseService):
    def get_revenue_list(franchise, filters) -> Dict
    def get_payouts_list(franchise, filters) -> Dict
    def request_payout(franchise, amount, bank_details) -> PayoutRequest
    def get_vendor_payouts_list(franchise, filters) -> Dict
    def approve_vendor_payout(franchise, payout_id, notes) -> PayoutRequest
    def complete_vendor_payout(franchise, payout_id, notes) -> PayoutRequest
    def reject_vendor_payout(franchise, payout_id, reason) -> PayoutRequest
```

### Serializers: `payout_serializers.py`
- `RevenueDistributionSerializer`
- `PayoutRequestSerializer`
- `CreatePayoutRequestSerializer`
- `VendorPayoutSerializer`
- `ApprovePayoutSerializer`
- `CompletePayoutSerializer`
- `RejectPayoutSerializer`

### Views: `franchise_payout_view.py`
- `FranchiseRevenueView` (GET)
- `FranchisePayoutView` (GET, POST)
- `FranchiseVendorPayoutView` (GET)
- `FranchiseVendorPayoutApproveView` (PATCH)
- `FranchiseVendorPayoutCompleteView` (PATCH)
- `FranchiseVendorPayoutRejectView` (PATCH)

---

## 4. Critical Validations

### Revenue Endpoint:
- ✅ Only franchise's stations (franchise_id match)
- ✅ Date range validation
- ✅ Pagination

### Request Payout:
- ✅ Amount > 0
- ✅ Amount <= franchise.balance
- ✅ Bank details required
- ✅ No pending payout exists

### Vendor Payout Complete:
- ✅ Verify vendor belongs to franchise
- ✅ Check franchise.balance >= amount
- ✅ Atomic transaction (deduct both balances)
- ✅ Status validation

---

## 5. Testing Checklist

### Revenue:
- [ ] List all transactions
- [ ] Filter by station
- [ ] Filter by vendor
- [ ] Filter by date range
- [ ] Summary calculations correct
- [ ] Pagination works

### Own Payouts:
- [ ] List own payouts
- [ ] Request payout (success)
- [ ] Request payout (insufficient balance)
- [ ] Request payout (duplicate pending)

### Vendor Payouts:
- [ ] List vendor payouts
- [ ] Approve vendor payout
- [ ] Complete vendor payout (balance deducted)
- [ ] Reject vendor payout
- [ ] Access control (other franchise cannot access)

---

## 6. Ready for Implementation

**Estimated Time:** 4-5 hours

**Dependencies:**
- ✅ PayoutRequest model exists
- ✅ RevenueDistribution model exists
- ✅ PayoutRequestRepository exists
- ✅ RevenueDistributionRepository exists

**Next Step:** Review this plan, then implement service → serializers → views → test
