from __future__ import annotations

from api.user.stations.views import router

urlpatterns = [
    *router.urls,
]
