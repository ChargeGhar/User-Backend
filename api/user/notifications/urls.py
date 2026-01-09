from __future__ import annotations

from api.user.notifications.views import router

urlpatterns = [
    *router.urls,
]
