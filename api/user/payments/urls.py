from __future__ import annotations

from django.urls import path, include
from api.user.payments.views import router
from api.user.payments.view_callbacks.callbacks import router as callback_router

urlpatterns = [
    path("", include(router.urls)),
    path("", include(callback_router.urls)),
]
