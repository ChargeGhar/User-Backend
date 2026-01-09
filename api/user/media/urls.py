from __future__ import annotations

from django.urls import path, include

from api.user.media.views import router

app_name = 'media'

urlpatterns = [
    path('', include(router.urls)),
]
