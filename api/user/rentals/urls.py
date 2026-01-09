from __future__ import annotations

from django.urls import path, include
from api.user.rentals.views import router

urlpatterns = [
    path("", include(router.urls)),
]
