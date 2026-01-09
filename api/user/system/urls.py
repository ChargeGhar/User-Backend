from __future__ import annotations

from django.urls import path, include

from api.user.system.views import router

app_name = 'system'

urlpatterns = [
    path('', include(router.urls)),
]
