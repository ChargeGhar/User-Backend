"""
Rental Serializers Package
==========================

Split into logical modules for maintainability:
- list_serializers: Minimal serializers for list views
- detail_serializers: Complete serializers for single item views
- action_serializers: Request payload serializers
- filter_serializers: Query parameter serializers
- stats_serializers: Statistics response serializers
"""

# List serializers
from .list_serializers import (
    RentalPackageListSerializer,
    RentalListSerializer,
)

# Detail serializers
from .detail_serializers import (
    RentalDetailSerializer,
    RentalExtensionSerializer,
    RentalIssueSerializer,
    RentalLocationSerializer,
)

# Action serializers
from .action_serializers import (
    RentalStartSerializer,
    RentalCancelSerializer,
    RentalExtensionCreateSerializer,
    RentalPayDueSerializer,
    RentalIssueCreateSerializer,
    RentalLocationUpdateSerializer,
    RentalSwapSerializer,
)

# Filter serializers
from .filter_serializers import (
    RentalHistoryFilterSerializer,
)

# Stats serializers
from .stats_serializers import (
    RentalStatsSerializer,
)


__all__ = [
    # List
    "RentalPackageListSerializer",
    "RentalListSerializer",
    # Detail
    "RentalDetailSerializer",
    "RentalExtensionSerializer",
    "RentalIssueSerializer",
    "RentalLocationSerializer",
    # Action
    "RentalStartSerializer",
    "RentalCancelSerializer",
    "RentalExtensionCreateSerializer",
    "RentalPayDueSerializer",
    "RentalIssueCreateSerializer",
    "RentalLocationUpdateSerializer",
    "RentalSwapSerializer",
    # Filter
    "RentalHistoryFilterSerializer",
    # Stats
    "RentalStatsSerializer",
]
