from api.common.mixins.response import StandardResponseMixin
from api.common.mixins.service import ServiceHandlerMixin
from api.common.mixins.cache import CacheableMixin
from api.common.mixins.pagination import PaginationMixin
from api.common.mixins.filter import FilterMixin

class BaseAPIView(
    StandardResponseMixin,
    ServiceHandlerMixin,
    CacheableMixin,
    PaginationMixin,
    FilterMixin
):
    """Base view combining all common mixins"""
    pass
