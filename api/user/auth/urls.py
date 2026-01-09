from __future__ import annotations

from api.user.auth.views import router

urlpatterns = [
    *router.urls,
]
