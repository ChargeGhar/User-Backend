"""
Country operations and search
"""
from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.system.services import CountryService
from api.user.system.serializers import CountryListSerializer
from api.common.services.base import ServiceException

country_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@country_router.register(r"app/countries", name="countries")
class CountryListView(ListAPIView):
    """Get list of countries with dialing codes"""
    serializer_class = CountryListSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=["App"],
        summary="Get Country Codes",
        description="Returns a list of countries with dialing codes (e.g., +977 for Nepal).",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        service = CountryService()
        return service.get_active_countries()

