# Database & Metadata Field Usage Analysis

**Date:** 2026-02-13 22:39  
**Goal:** Track all database fields and metadata usage in rental start vs pay-due

---

## Analysis Plan

### Phase 1: Identify All Fields
1. Rental model fields
2. Transaction model fields
3. PaymentIntent metadata
4. Rental metadata

### Phase 2: Track Usage
1. Rental Start - which fields are set/read
2. Pay Due - which fields are set/read
3. Compare for consistency

### Phase 3: Find Issues
1. Mismatches in field usage
2. Inconsistent metadata keys
3. Missing fields
4. Duplicate/conflicting data

---

## Step 1: Get Model Definitions

Let me extract the actual model fields from code...
