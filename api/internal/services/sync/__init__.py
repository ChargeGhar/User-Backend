"""
Station sync service - modular structure
"""
from __future__ import annotations

from api.internal.services.sync.base import StationSyncBaseMixin
from api.internal.services.sync.station import StationSyncMixin
from api.internal.services.sync.return_event import ReturnEventMixin
from api.internal.services.sync.status import StatusUpdateMixin

from api.common.services.base import CRUDService
from api.user.stations.models import Station


class StationSyncService(
    StationSyncMixin,
    ReturnEventMixin,
    StatusUpdateMixin,
    StationSyncBaseMixin,
    CRUDService
):
    """
    Service for processing station data from IoT system
    Combines all sync operations via mixins
    """
    model = Station


__all__ = ['StationSyncService']
