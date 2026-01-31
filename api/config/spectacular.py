"""
DRF Spectacular OpenAPI Configuration
======================================

This configuration lets DRF Spectacular auto-discover all endpoints from URL routing.
We use @extend_schema decorators in views to provide metadata (operation_id, tags, descriptions).

No manual endpoint filtering or collision fixes needed - the framework handles it automatically.
"""
from __future__ import annotations

from api import __version__
from api.config.application import PROJECT_VERBOSE_NAME


SPECTACULAR_SETTINGS = {
    # Project Information
    "TITLE": f"{PROJECT_VERBOSE_NAME} API",
    "DESCRIPTION": (
        "ChargeGhar API - Shared Power Bank Network for Nepal. "
        "Complete REST API documentation for mobile and web clients."
    ),
    "VERSION": __version__,
    "CONTACT": {
        "name": "ChargeGhar API Support",
        "email": "support@chargegh.com",
    },
    "LICENSE": {
        "name": "Proprietary",
    },
    
    # Schema Generation
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "COMPONENT_SPLIT_REQUEST": True,

    # Endpoint Organization (tags defined in @extend_schema decorators)
    "TAGS": [
        {"name": "App", "description": "Core app functionality (health, version, media, countries)"},
        {"name": "Authentication - OTP", "description": "OTP-based authentication (request, verify, complete)"},
        {"name": "Authentication - Biometric", "description": "Biometric authentication (fingerprint, Face ID)"},
        {"name": "Authentication - Social", "description": "Social authentication (Google, Apple OAuth)"},
        {"name": "Authentication - Session", "description": "Session management (logout, token refresh)"},
        {"name": "Authentication - Profile", "description": "User profile and account management"},
        {"name": "Authentication - KYC", "description": "KYC document submission and verification"},
        {"name": "Stations", "description": "Charging station discovery, favorites, and issue reporting"},
        {"name": "Notifications", "description": "Real-time user notifications and alerts"},
        {"name": "Payments", "description": "Wallet management, transactions, and payment gateways"},
        {"name": "Rentals", "description": "Power bank rental operations and history"},
        {"name": "Points", "description": "Reward points and referral system"},
        {"name": "Promotions", "description": "Coupon management and promotional campaigns"},
        {"name": "Social", "description": "Social features, achievements, and leaderboards"},
        {"name": "Content", "description": "App content and information pages"},
        {"name": "Advertisements", "description": "User advertisement request submission and management"},
        {"name": "Admin", "description": "Administrative operations and analytics"},
        {"name": "Admin - Advertisements", "description": "Admin advertisement review, approval, and management"},
        {"name": "Partner Auth", "description": "Partner authentication (Franchise & Revenue Vendor dashboard login)"},
        {"name": "Partner - Franchise", "description": "Franchise dashboard (vendors, revenue, payouts)"},
        {"name": "Partner - Vendor", "description": "Vendor dashboard (station, revenue, payouts)"},
        {"name": "Partner - Common", "description": "Partner Common API Endpoints"},
    ],
    
    # UI Configuration
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
}