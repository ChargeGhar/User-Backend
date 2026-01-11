# Internal IoT Integration

## Overview

This app handles internal API endpoints for IoT system integration with the Java IoT management system.

## Deployment Architecture

- **Java IoT System**: `https://api.chargeghar.com:8080` (213.210.21.113:8080)
- **Django Main App**: `https://main.chargeghar.com:8010` (213.210.21.113:8010)

## Environment Variables

```bash
# IoT System Integration
IOT_SYSTEM_SIGNATURE_SECRET=your-production-secret-key-here-min-32-chars
IOT_SYSTEM_ALLOWED_IPS=127.0.0.1,213.210.21.113,api.chargeghar.com
IOT_SYSTEM_SIGNATURE_TIMEOUT=300
```

## API Endpoint

**URL**: `POST /api/internal/stations/data`

**Authentication**: Admin user + HMAC signature validation

**Headers**:
- `Authorization: Bearer <admin_access_token>`
- `X-Signature: <hmac_sha256_signature>`
- `X-Timestamp: <unix_timestamp>`
- `Content-Type: application/json`

## Request Types

### Full Station Sync (`type=full`)
Complete station synchronization with slots and powerbanks.

### PowerBank Return Event (`type=returned`)
Notification when a powerbank is returned to a station.

### Status Update (`type=status`)
Device status change (online/offline/maintenance).

## Service Structure

```
api/internal/services/sync/
├── __init__.py      # StationSyncService (combines mixins)
├── base.py          # Status mappings and validation helpers
├── station.py       # Full sync operations
├── return_event.py  # Return event processing
└── status.py        # Status update handling
```

## Testing

```bash
python manage.py test api.internal.tests
```

## Troubleshooting

1. **Signature Validation Failed**: Verify `IOT_SYSTEM_SIGNATURE_SECRET` matches Java config
2. **Authentication Failed**: Ensure admin user has `is_staff=True`
3. **Station Not Found**: Station auto-creates on first sync
