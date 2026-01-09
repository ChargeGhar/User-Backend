from __future__ import annotations

from api.user.content.views import router

urlpatterns = [
    *router.urls,
]
