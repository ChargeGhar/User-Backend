from __future__ import annotations

from api.user.points.views import router

urlpatterns = [
    *router.urls,
]
