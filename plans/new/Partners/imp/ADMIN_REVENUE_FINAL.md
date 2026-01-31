# ADMIN REVENUE ENDPOINT - SIMPLIFIED & ACCURATE

## RESPONSE FORMAT (Centered on RevenueDistribution)

### Single Revenue Item (Clean & Readable)
```json
{
  "id": "uuid",
  "created_at": "2026-01-31T10:00:00Z",
  
  // Financial Breakdown (Core Data)
  "gross_amount": "100.00",
  "vat_amount": "13.00",
  "service_charge": "5.00",
  "net_amount": "82.00",
  "chargeghar_share": "41.00",
  "franchise_share": "24.60",
  "vendor_share": "16.40",
  
  // Distribution Status
  "is_distributed": true,
  "distributed_at": "2026-01-31T10:05:00Z",
  
  // Transaction Info (Related)
  "transaction_id": "TXN123456",
  "transaction_status": "SUCCESS",
  "payment_method": "KHALTI",
  "user_email": "user@example.com",
  
  // Rental Info (Related)
  "rental_code": "RNT12345",
  "rental_status": "COMPLETED",
  "started_at": "2026-01-31T09:00:00Z",
  "ended_at": "2026-01-31T10:00:00Z",
  
  // Station Info (Related)
  "station_name": "Chitwan Mall Station",
  "station_sn": "CTW001",
  
  // Partner Info (Related - if exists)
  "franchise_code": "FR-001",
  "franchise_name": "Pro Boy",
  "vendor_code": "VN-003",
  "vendor_name": "Vendor ABC",
  
  // Audit Trail
  "is_reversal": false,
  "reversal_reason": null
}
```

## IMPLEMENTATION

### Service Method (_format_revenue_item)
```python
def _format_revenue_item(rd) -> Dict:
    """Format revenue distribution - flat, readable structure"""
    return {
        # Revenue Distribution Core
        'id': str(rd.id),
        'created_at': rd.created_at.isoformat(),
        
        # Financial Breakdown
        'gross_amount': rd.gross_amount,
        'vat_amount': rd.vat_amount,
        'service_charge': rd.service_charge,
        'net_amount': rd.net_amount,
        'chargeghar_share': rd.chargeghar_share,
        'franchise_share': rd.franchise_share,
        'vendor_share': rd.vendor_share,
        
        # Distribution Status
        'is_distributed': rd.is_distributed,
        'distributed_at': rd.distributed_at.isoformat() if rd.distributed_at else None,
        
        # Transaction (Related)
        'transaction_id': rd.transaction.transaction_id,
        'transaction_status': rd.transaction.status,
        'payment_method': rd.transaction.payment_method_type,
        'user_email': rd.transaction.user.email,
        
        # Rental (Related - if exists)
        'rental_code': rd.rental.rental_code if rd.rental else None,
        'rental_status': rd.rental.status if rd.rental else None,
        'started_at': rd.rental.started_at.isoformat() if rd.rental and rd.rental.started_at else None,
        'ended_at': rd.rental.ended_at.isoformat() if rd.rental and rd.rental.ended_at else None,
        
        # Station (Related)
        'station_name': rd.station.station_name,
        'station_sn': rd.station.serial_number,
        
        # Partners (Related - if exist)
        'franchise_code': rd.franchise.code if rd.franchise else None,
        'franchise_name': rd.franchise.business_name if rd.franchise else None,
        'vendor_code': rd.vendor.code if rd.vendor else None,
        'vendor_name': rd.vendor.business_name if rd.vendor else None,
        
        # Audit Trail
        'is_reversal': rd.is_reversal,
        'reversal_reason': rd.reversal_reason if rd.reversal_reason else None,
    }
```

### Serializer (Single, Flat)
```python
class AdminRevenueItemSerializer(serializers.Serializer):
    """Admin revenue item - flat, readable structure"""
    # Revenue Distribution Core
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    
    # Financial Breakdown
    gross_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    service_charge = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    chargeghar_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    franchise_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    vendor_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Distribution Status
    is_distributed = serializers.BooleanField()
    distributed_at = serializers.DateTimeField(allow_null=True)
    
    # Transaction (Related)
    transaction_id = serializers.CharField()
    transaction_status = serializers.CharField()
    payment_method = serializers.CharField()
    user_email = serializers.EmailField()
    
    # Rental (Related)
    rental_code = serializers.CharField(allow_null=True)
    rental_status = serializers.CharField(allow_null=True)
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)
    
    # Station (Related)
    station_name = serializers.CharField()
    station_sn = serializers.CharField()
    
    # Partners (Related)
    franchise_code = serializers.CharField(allow_null=True)
    franchise_name = serializers.CharField(allow_null=True)
    vendor_code = serializers.CharField(allow_null=True)
    vendor_name = serializers.CharField(allow_null=True)
    
    # Audit Trail
    is_reversal = serializers.BooleanField()
    reversal_reason = serializers.CharField(allow_null=True)
```

## BENEFITS

✅ **Flat Structure** - Easy to read, no nested objects
✅ **Revenue-Centric** - Starts with financial data (the main point)
✅ **Natural Flow** - Financial → Distribution → Transaction → Rental → Station → Partners → Audit
✅ **Minimal Fields** - Only essential auditable data
✅ **Null-Safe** - Handles optional rental, franchise, vendor gracefully
✅ **Single Serializer** - No nested serializers needed

## COMPLETE RESPONSE

```json
{
  "success": true,
  "message": "Revenue data retrieved successfully",
  "data": {
    "results": [
      {
        "id": "uuid",
        "created_at": "2026-01-31T10:00:00Z",
        "gross_amount": "100.00",
        "vat_amount": "13.00",
        "service_charge": "5.00",
        "net_amount": "82.00",
        "chargeghar_share": "41.00",
        "franchise_share": "24.60",
        "vendor_share": "16.40",
        "is_distributed": true,
        "distributed_at": "2026-01-31T10:05:00Z",
        "transaction_id": "TXN123456",
        "transaction_status": "SUCCESS",
        "payment_method": "KHALTI",
        "user_email": "user@example.com",
        "rental_code": "RNT12345",
        "rental_status": "COMPLETED",
        "started_at": "2026-01-31T09:00:00Z",
        "ended_at": "2026-01-31T10:00:00Z",
        "station_name": "Chitwan Mall Station",
        "station_sn": "CTW001",
        "franchise_code": "FR-001",
        "franchise_name": "Pro Boy",
        "vendor_code": "VN-003",
        "vendor_name": "Vendor ABC",
        "is_reversal": false,
        "reversal_reason": null
      }
    ],
    "summary": {
      "total_transactions": 150,
      "total_gross": "15000.00",
      "total_vat": "1950.00",
      "total_service_charge": "750.00",
      "total_net": "12300.00",
      "total_chargeghar_share": "6150.00",
      "total_franchise_share": "3690.00",
      "total_vendor_share": "2460.00"
    },
    "pagination": {
      "current_page": 1,
      "total_pages": 8,
      "total_count": 150,
      "page_size": 20,
      "has_next": true,
      "has_previous": false,
      "next_page": 2,
      "previous_page": null
    }
  }
}
```

## READY FOR IMPLEMENTATION

✅ Flat, readable structure
✅ Revenue-centric design
✅ All fields verified from models
✅ Minimal, essential data only
✅ Single serializer (no nesting)
