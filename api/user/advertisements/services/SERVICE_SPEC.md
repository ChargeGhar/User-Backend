# Advertisement Services Specification

## ✅ **USER SERVICES**

### **AdRequestService**

#### **Method: `create_ad_request(user, validated_data)`**
**Business Rules:**
- ✅ User must provide: full_name, contact_number, media_upload_id
- ✅ Media upload must exist and belong to user
- ✅ Media must be IMAGE or VIDEO type only
- ✅ AdRequest created with status='SUBMITTED', submitted_at=now()
- ✅ AdContent created with: content_type from media, duration_seconds=5, display_order=0, is_active=True
- ✅ Uses @transaction.atomic for data consistency
- ✅ Logs creation with user info

**Repository Calls:**
- ✅ `MediaUpload.objects.get()` - Validate media
- ✅ `AdRequestRepository.create()` - Create ad request
- ✅ `AdContentRepository.create()` - Create content

**Exceptions:**
- ✅ ServiceException("media_not_found") - Media doesn't exist or wrong user
- ✅ ServiceException("invalid_media_type") - Not IMAGE or VIDEO

---

#### **Method: `get_user_ad_requests(user, filters)`**
**Business Rules:**
- ✅ Only return ads belonging to user
- ✅ Support optional status filter
- ✅ Return QuerySet for pagination
- ✅ Include all relations (transaction, content, stations)

**Repository Calls:**
- ✅ `AdRequestRepository.get_user_ad_requests(user, status)`

**Returns:** QuerySet[AdRequest]

---

#### **Method: `get_user_ad_by_id(ad_id, user)`**
**Business Rules:**
- ✅ Ad must belong to user
- ✅ Include all relations

**Repository Calls:**
- ✅ `AdRequestRepository.get_by_id_for_user(ad_id, user)`

**Exceptions:**
- ✅ ServiceException("ad_not_found") - Ad doesn't exist or wrong user

---

### **AdPaymentService**

#### **Method: `process_ad_payment(ad_request_id, user)`**
**Business Rules:**
- ✅ Ad must belong to user
- ✅ Ad status must be 'PENDING_PAYMENT'
- ✅ admin_price must be set and > 0
- ✅ User wallet must exist and be active
- ✅ Wallet balance must be >= admin_price
- ✅ Create Transaction: type='ADVERTISEMENT', status='SUCCESS', payment_method_type='WALLET'
- ✅ Generate unique transaction_id using generate_transaction_id()
- ✅ Create WalletTransaction for audit trail with balance_before and balance_after
- ✅ Deduct from wallet balance
- ✅ Update ad: transaction, paid_at=now(), status='PAID'
- ✅ Uses @transaction.atomic with select_for_update() for row-level locking
- ✅ Logs payment with transaction ID

**Repository Calls:**
- ✅ `AdRequest.objects.select_for_update().get()` - Get ad with lock
- ✅ `Wallet.objects.select_for_update().get()` - Get wallet with lock
- ✅ `Transaction.objects.create()` - Create transaction
- ✅ `WalletTransaction.objects.create()` - Create wallet transaction
- ✅ `wallet.save()` - Update balance
- ✅ `ad_request.save()` - Update ad

**Exceptions:**
- ✅ ServiceException("ad_not_found") - Ad doesn't exist or wrong user
- ✅ ServiceException("invalid_ad_status") - Not PENDING_PAYMENT
- ✅ ServiceException("price_not_set") - admin_price not set or <= 0
- ✅ ServiceException("wallet_not_found") - Wallet doesn't exist or inactive
- ✅ ServiceException("insufficient_balance") - Balance < admin_price

---

## ✅ **ADMIN SERVICES**

### **AdminAdService**

#### **Method: `get_ad_requests(filters)`**
**Business Rules:**
- ✅ Return all ads (no user restriction)
- ✅ Support filters: status, user_id, search
- ✅ Search in: title, full_name, user.username, user.email
- ✅ Return QuerySet for pagination
- ✅ Include all relations

**Repository Calls:**
- ✅ `AdRequestRepository.get_all_ad_requests(filters)`

**Returns:** QuerySet[AdRequest]

---

#### **Method: `get_ad_request_detail(ad_id)`**
**Business Rules:**
- ✅ No user restriction (admin can see all)
- ✅ Include all relations

**Repository Calls:**
- ✅ `AdRequestRepository.get_by_id(ad_id)`

**Exceptions:**
- ✅ ServiceException("ad_not_found") - Ad doesn't exist

---

#### **Method: `review_ad_request(ad_id, admin_user, validated_data)`**
**Business Rules:**
- ✅ Valid statuses: SUBMITTED, UNDER_REVIEW
- ✅ Set status to UNDER_REVIEW
- ✅ Update: title, description, duration_days, admin_price, admin_notes, start_date
- ✅ Calculate end_date if start_date and duration_days provided
- ✅ Update AdContent: duration_seconds, display_order
- ✅ Validate all stations exist
- ✅ Clear and recreate AdDistribution records
- ✅ Set reviewed_by and reviewed_at
- ✅ Uses @transaction.atomic with select_for_update()
- ✅ Logs review with admin, price, station count

**Repository Calls:**
- ✅ `AdRequest.objects.select_for_update().get()` - Get ad with lock
- ✅ `Station.objects.filter()` - Validate stations
- ✅ `ad_request.save()` - Update ad
- ✅ `AdContentRepository.get_by_ad_request()` - Get content
- ✅ `AdContentRepository.update()` - Update content
- ✅ `AdDistributionRepository.delete_by_ad_content()` - Clear distributions
- ✅ `AdDistributionRepository.create()` - Create distributions (loop)

**Exceptions:**
- ✅ ServiceException("ad_not_found") - Ad doesn't exist
- ✅ ServiceException("invalid_status") - Not SUBMITTED or UNDER_REVIEW
- ✅ ServiceException("stations_not_found") - One or more stations don't exist

---

#### **Method: `perform_ad_action(ad_id, admin_user, action, data)`**
**Business Rules:**

**APPROVE:**
- ✅ Valid status: UNDER_REVIEW
- ✅ Set: status='APPROVED', approved_by, approved_at
- ✅ Auto-transition to PENDING_PAYMENT if admin_price > 0

**REJECT:**
- ✅ Valid statuses: SUBMITTED, UNDER_REVIEW
- ✅ Requires rejection_reason
- ✅ Set: status='REJECTED', rejection_reason, reviewed_by, reviewed_at

**SCHEDULE:**
- ✅ Valid status: PAID
- ✅ Requires start_date
- ✅ Calculate end_date if not provided (start_date + duration_days)
- ✅ Set: status='SCHEDULED', start_date, end_date

**PAUSE:**
- ✅ Valid status: RUNNING
- ✅ Set: status='PAUSED'

**RESUME:**
- ✅ Valid status: PAUSED
- ✅ Set: status='RUNNING'

**CANCEL:**
- ✅ Valid statuses: Any except COMPLETED
- ✅ Optional reason appended to admin_notes
- ✅ Set: status='CANCELLED'

**COMPLETE:**
- ✅ Valid status: RUNNING
- ✅ Set: status='COMPLETED', completed_at=now()

**Repository Calls:**
- ✅ `AdRequest.objects.select_for_update().get()` - Get ad with lock
- ✅ `ad_request.save()` - Update ad

**Exceptions:**
- ✅ ServiceException("ad_not_found") - Ad doesn't exist
- ✅ ServiceException("invalid_action") - Unknown action
- ✅ ServiceException("invalid_status") - Wrong status for action
- ✅ ServiceException("rejection_reason_required") - Reject without reason
- ✅ ServiceException("start_date_required") - Schedule without start_date

---

#### **Method: `update_schedule(ad_id, validated_data)`**
**Business Rules:**
- ✅ Valid statuses: SCHEDULED, RUNNING, PAUSED
- ✅ At least one of start_date or end_date must be provided
- ✅ Uses @transaction.atomic with select_for_update()
- ✅ Logs schedule update

**Repository Calls:**
- ✅ `AdRequest.objects.select_for_update().get()` - Get ad with lock
- ✅ `ad_request.save()` - Update ad

**Exceptions:**
- ✅ ServiceException("ad_not_found") - Ad doesn't exist
- ✅ ServiceException("invalid_status") - Not SCHEDULED/RUNNING/PAUSED

---

## ✅ **CROSS-VERIFICATION**

### **Repository Integration**
- ✅ All repository methods used correctly
- ✅ Proper use of select_related/prefetch_related through repositories
- ✅ Row-level locking where needed (payment, review, actions)
- ✅ QuerySet returned for pagination support

### **Transaction Management**
- ✅ @transaction.atomic on all write operations
- ✅ select_for_update() for concurrent safety
- ✅ Proper rollback on exceptions

### **Error Handling**
- ✅ ServiceException with specific error codes
- ✅ Proper exception propagation
- ✅ Logging on all operations

### **Business Logic**
- ✅ All status transitions validated
- ✅ All required fields validated
- ✅ Auto-calculations (end_date, auto-transition)
- ✅ Audit trail (WalletTransaction, admin fields)

### **View Layer Expectations**
- ✅ Services return models or QuerySets (not dicts)
- ✅ Views will serialize using serializers
- ✅ Pagination handled by views using QuerySets
- ✅ Exceptions caught by view error handlers

---

## ✅ **100% READY FOR VIEWS**

All services are:
- ✅ Accurate to business rules
- ✅ Consistent with project patterns
- ✅ Properly integrated with repositories
- ✅ Transaction-safe
- ✅ Error-handled
- ✅ Logged
- ✅ Ready for view layer
