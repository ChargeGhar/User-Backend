# Advertisement Repositories Specification

## ✅ **AdRequestRepository**

### **Query Methods**
- ✅ `get_by_id(ad_id)` - Get single ad with all relations (user, transaction, reviewed_by, approved_by, contents, distributions, stations)
- ✅ `get_by_id_for_user(ad_id, user)` - Get ad for specific user (for user endpoints)
- ✅ `get_user_ad_requests(user, status=None)` - Get user's ads with optional status filter
- ✅ `get_all_ad_requests(filters=None)` - Get all ads with filters (status, user_id, search) for admin
- ✅ `get_scheduled_ads_to_start(today)` - For cron job to start scheduled ads
- ✅ `get_running_ads_to_complete(today)` - For cron job to complete finished ads
- ✅ `get_active_ads_for_user(user)` - Get user's RUNNING or SCHEDULED ads

### **Write Methods**
- ✅ `create(user, **kwargs)` - Create new ad request
- ✅ `update(ad_request, **kwargs)` - Update existing ad request

### **Count Methods**
- ✅ `count_by_status(status)` - Count ads by status
- ✅ `count_by_user(user)` - Count user's ads

### **Optimizations**
- ✅ Uses `select_related()` for ForeignKey relations (user, transaction, reviewed_by, approved_by)
- ✅ Uses `prefetch_related()` for reverse relations (ad_contents, ad_distributions, stations)
- ✅ Returns QuerySet (not list) for pagination support
- ✅ Filters applied at database level

---

## ✅ **AdContentRepository**

### **Query Methods**
- ✅ `get_by_id(content_id)` - Get single content with relations
- ✅ `get_by_ad_request(ad_request_id)` - Get first active content for ad request
- ✅ `get_all_by_ad_request(ad_request_id)` - Get all contents for ad request
- ✅ `get_active_contents_by_ad_request(ad_request_id)` - Get only active contents

### **Write Methods**
- ✅ `create(ad_request, **kwargs)` - Create new content
- ✅ `update(ad_content, **kwargs)` - Update existing content
- ✅ `deactivate_all_for_ad_request(ad_request_id)` - Deactivate all contents
- ✅ `delete(ad_content)` - Delete content

### **Count Methods**
- ✅ `count_by_ad_request(ad_request_id)` - Count all contents
- ✅ `count_active_by_ad_request(ad_request_id)` - Count active contents

### **Optimizations**
- ✅ Uses `select_related()` for ad_request and media_upload
- ✅ Uses `prefetch_related()` for ad_distributions
- ✅ Returns list for small result sets
- ✅ Ordered by display_order, -created_at

---

## ✅ **AdDistributionRepository**

### **Query Methods**
- ✅ `get_by_id(distribution_id)` - Get single distribution
- ✅ `get_by_ad_content(ad_content_id)` - Get all distributions for content
- ✅ `get_by_station(station_id)` - Get all distributions for station
- ✅ `get_active_by_station(station_id)` - Get only RUNNING ads for station
- ✅ `get_stations_for_ad_content(ad_content_id)` - Get list of Station objects

### **Write Methods**
- ✅ `create(ad_content, station, **kwargs)` - Create single distribution
- ✅ `bulk_create(distributions)` - Bulk create distributions
- ✅ `delete_by_ad_content(ad_content_id)` - Delete all for content
- ✅ `delete_by_station(ad_content_id, station_id)` - Delete specific distribution

### **Check Methods**
- ✅ `exists(ad_content_id, station_id)` - Check if distribution exists

### **Count Methods**
- ✅ `count_by_ad_content(ad_content_id)` - Count distributions for content
- ✅ `count_by_station(station_id)` - Count distributions for station

### **Optimizations**
- ✅ Uses `select_related()` for ad_content, ad_request, station, media_upload
- ✅ Returns list for small result sets
- ✅ Supports bulk operations

---

## **Service Layer Requirements Met**

### **User Service (AdRequestService)**
✅ `create_ad_request()` needs:
- `AdRequestRepository.create(user, **kwargs)`
- `AdContentRepository.create(ad_request, **kwargs)`

✅ `get_user_ad_requests()` needs:
- `AdRequestRepository.get_user_ad_requests(user, filters)`

### **Payment Service (AdPaymentService)**
✅ `process_ad_payment()` needs:
- `AdRequestRepository.get_by_id_for_user(ad_id, user)` with `select_for_update()`
- `AdRequestRepository.update(ad_request, **kwargs)`

### **Admin Service (AdminAdService)**
✅ `get_ad_requests()` needs:
- `AdRequestRepository.get_all_ad_requests(filters)`

✅ `get_ad_request_detail()` needs:
- `AdRequestRepository.get_by_id(ad_id)`

✅ `review_ad_request()` needs:
- `AdRequestRepository.get_by_id(ad_id)` with `select_for_update()`
- `AdContentRepository.get_by_ad_request(ad_request_id)`
- `AdContentRepository.update(ad_content, **kwargs)`
- `AdDistributionRepository.delete_by_ad_content(ad_content_id)`
- `AdDistributionRepository.create(ad_content, station, **kwargs)`

✅ `perform_ad_action()` needs:
- `AdRequestRepository.get_by_id(ad_id)` with `select_for_update()`
- `AdRequestRepository.update(ad_request, **kwargs)`

### **Celery Tasks**
✅ `start_scheduled_ads()` needs:
- `AdRequestRepository.get_scheduled_ads_to_start(today)`

✅ `complete_finished_ads()` needs:
- `AdRequestRepository.get_running_ads_to_complete(today)`

---

## **Pattern Consistency**

✅ **Follows existing repository patterns:**
- Static methods (no instance state)
- Type hints for all parameters and returns
- Docstrings for all methods
- Returns `Optional[Model]` for single objects
- Returns `List[Model]` for small result sets
- Returns `QuerySet` for pagination support
- Uses `select_related()` and `prefetch_related()` for optimization
- Consistent naming: `get_by_*`, `get_all_*`, `create`, `update`, `delete`, `count_*`
- Exception handling with try/except for DoesNotExist

✅ **No assumptions made:**
- All methods match exact service layer needs
- All relations properly loaded
- All filters properly applied
- All optimizations in place

---

## **100% Ready for Service Layer** ✅
