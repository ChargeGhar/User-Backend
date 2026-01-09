# IoT Integration Setup Guide

## 🌐 Deployment Architecture

- **Java IoT System**: `https://api.chargeghar.com:8080` (213.210.21.113:8080)
- **Django Main App**: `https://main.chargeghar.com:8010` (213.210.21.113:8010)

## 🔧 Environment Variables

Add these to your `.env` file:

```bash
# IoT System Integration
IOT_SYSTEM_SIGNATURE_SECRET=your-production-secret-key-here-min-32-chars
IOT_SYSTEM_ALLOWED_IPS=127.0.0.1,213.210.21.113,api.chargeghar.com
IOT_SYSTEM_SIGNATURE_TIMEOUT=300
```

## 🚀 API Endpoint

**URL**: `POST https://main.chargeghar.com:8010/api/internal/stations/data`

**Authentication**: Requires admin user authentication + HMAC signature validation

**Headers Required**:
- `Authorization: Bearer <admin_access_token>`
- `X-Signature: <hmac_sha256_signature>`
- `X-Timestamp: <unix_timestamp>`
- `Content-Type: application/json`

## 📊 Request Types

### Full Station Sync
```json
{
  "type": "full",
  "timestamp": 1698345600,
  "device": {
    "serial_number": "864601069946994",
    "status": "ONLINE",
    "last_heartbeat": "2025-10-27T14:30:00Z"
  },
  "station": {
    "total_slots": 4
  },
  "slots": [...],
  "power_banks": [...]
}
```

### PowerBank Return Event
```json
{
  "type": "returned",
  "timestamp": 1698345600,
  "device": {
    "serial_number": "864601069946994"
  },
  "return_event": {
    "power_bank_serial": "123456789",
    "slot_number": 3,
    "battery_level": 45
  }
}
```

## 🧪 Testing

Run the integration tests:
```bash
python manage.py test api.stations.tests.test_iot_integration
```

## 🔍 Monitoring

Check logs for integration activity:
```bash
# View Django logs
tail -f logs/django.log | grep "StationDataInternalView\|StationSyncService"

# Check for signature validation issues
tail -f logs/django.log | grep "signature"
```

## 🚨 Troubleshooting

### Common Issues

1. **Signature Validation Failed**
   - Verify `IOT_SYSTEM_SIGNATURE_SECRET` matches Java config
   - Check timestamp is within 5 minutes
   - Ensure payload + timestamp concatenation is correct

2. **Authentication Failed**
   - Verify admin user credentials
   - Check JWT token is not expired
   - Ensure user has `is_staff=True` and `is_superuser=True`

3. **Station Not Found**
   - Station will be auto-created on first sync
   - Check serial_number format matches device

4. **PowerBank Not Found**
   - PowerBank will be auto-created on first sync
   - Verify serial_number in return event matches existing PowerBank