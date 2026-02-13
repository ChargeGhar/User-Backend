# Rental Start - Amount Calculation & Data Flow Test Plan

**Date:** 2026-02-13 23:04  
**Goal:** Verify amount calculations, discounts, points, and data flow accuracy

---

## Test Strategy

### Phase 1: Setup Test Data
1. Get actual package prices
2. Get actual discount configurations
3. Get actual station data
4. Set user balance/points

### Phase 2: Test Scenarios
1. Basic rental (no discount, wallet only)
2. Rental with discount
3. Rental with points
4. Rental with wallet + points
5. Rental with insufficient balance

### Phase 3: Verify Data Flow
1. Check database changes
2. Verify transaction records
3. Verify rental metadata
4. Verify balance deductions

---

## Step 1: Discover Actual Data

Let me query the database for real data...
