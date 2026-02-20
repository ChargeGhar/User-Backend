"""
Services package for stations app
============================================================

This package contains all service classes organized by functionality.
Maintains backward compatibility by re-exporting all services.
"""
from __future__ import annotations

from .station_service import StationService
from .station_favorite_service import StationFavoriteService
from .station_issue_service import StationIssueService
from .user_issue_report_service import UserIssueReportService
from .power_bank_service import PowerBankService
from .device_api_service import DeviceAPIService, get_device_api_service


# Backward compatibility - all services available at package level
__all__ = [
    "PowerBankService",
    "StationFavoriteService",
    "StationIssueService",
    "UserIssueReportService",
    "StationService",
    "DeviceAPIService",
    "get_device_api_service",
]
