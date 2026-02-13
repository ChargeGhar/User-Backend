# DUE.md - Quick Reference

**Created:** 2026-02-13 21:46  
**Status:** ✅ Complete - Ready for Cross-Verification

---

## Document Overview

**File:** `plans/DUE.md`  
**Total Scenarios:** 17 (15 main + 2 special cases)  
**Format:** Mirrors `Rental.md` structure

---

## Scenario Breakdown

### Success Scenarios (HTTP 200)
1. ✅ wallet + SUFFICIENT
2. ✅ points + SUFFICIENT
3. ✅ wallet_points + SUFFICIENT

### Payment Required (HTTP 402)
4. ✅ wallet + INSUFFICIENT
5. ✅ points + INSUFFICIENT
6. ✅ wallet_points + wallet short
7. ✅ wallet_points + points short
8. ✅ direct mode (always 402)

### Validation Errors (HTTP 400/404)
9. ✅ No dues pending (dues_already_paid)
10. ✅ Rental not found (404)
11. ✅ direct without payment_method_id
12. ✅ Insufficient without payment_method_id
13. ✅ Invalid payment_mode
14. ✅ Invalid payment_method_id
15. ✅ Rental not started (popup failed)

### Special Cases
16. ✅ OVERDUE - powerbank NOT returned (status stays OVERDUE)
17. ✅ OVERDUE - powerbank returned (status → COMPLETED)

---

## Key Features

### Response Format Standards
- ✅ Type 1: Success (HTTP 200)
- ✅ Type 2: Payment Required (HTTP 402)
- ✅ Type 3: Error (HTTP 4xx/5xx)

### Each Scenario Includes
- Setup (balance, points, rental state)
- Request payload
- Expected response (full JSON)
- Database changes
- Notes/explanations

### Field Definitions
- ✅ Success response fields table
- ✅ Payment required fields table
- ✅ Summary comparison table

---

## Consistency with Rental.md

| Aspect | Rental.md | DUE.md |
|--------|-----------|--------|
| Structure | ✅ | ✅ Same |
| Response types | 3 types | 3 types |
| Scenario format | Setup → Request → Response → DB | ✅ Same |
| Field naming | `breakdown` | ✅ `breakdown` |
| HTTP 402 | payment_required | ✅ payment_required |
| Flat structure | ✅ | ✅ |

---

## Differences from Rental Start

| Aspect | Rental Start | Pay Due |
|--------|--------------|---------|
| Success HTTP | 201 | 200 |
| Transaction type | RENTAL | RENTAL_DUE |
| Creates rental | Yes | No (updates) |
| Final status | PENDING_POPUP/ACTIVE | COMPLETED/OVERDUE |
| Powerbank check | Availability | Return status |

---

## Next Steps

### Phase 1: Cross-Verification
1. Compare DUE.md with current implementation
2. Verify each scenario response format
3. Check field naming consistency
4. Validate HTTP status codes

### Phase 2: Implementation
1. Create `due/response_builder.py`
2. Update `rental_due_service.py`
3. Update `support_views.py`
4. Add serializer validations

### Phase 3: Testing
1. Test all 17 scenarios
2. Verify database changes
3. Test both gateways (Khalti, eSewa)
4. Verify powerbank return logic

---

## Testing Priority

**High Priority (Core Flows):**
- Scenario 1, 2 (wallet)
- Scenario 3, 4 (points)
- Scenario 5, 6, 7 (wallet_points)
- Scenario 8 (direct)

**Medium Priority (Validations):**
- Scenario 9, 11, 12 (common errors)

**Low Priority (Edge Cases):**
- Scenario 10, 13, 14, 15 (rare errors)
- Special cases 16, 17 (OVERDUE handling)

---

## Document Quality

✅ **Complete:** All scenarios documented  
✅ **Consistent:** Matches Rental.md format  
✅ **Detailed:** Full request/response/DB changes  
✅ **Accurate:** Based on existing implementation  
✅ **Testable:** Clear setup and expected results  

---

**Status:** Ready for recursive cross-verification against codebase
