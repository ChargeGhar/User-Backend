Current Apps in api/ directory:
pycache
admin
common
config
content
media
notifications
payments
points
promotions
rentals
social
stations
system
users
web

Proposed Target Structure:
api/
├── admin/                    # Remains as-is
├── user/                     # New module containing user-facing apps
│   ├── auth/                 # Renamed from 'users'
│   ├── content/
│   ├── media/
│   ├── notifications/
│   ├── payments/
│   ├── points/
│   ├── promotions/
│   ├── rentals/
│   ├── social/
│   ├── stations/
│   └── system/
├── vendor/                   # New empty module (future vendor features)
├── franchise/                # New empty module (future franchise features)
├── common/                   # Remains as-is
├── config/                   # Remains as-is
└── web/                      # Remains as-is