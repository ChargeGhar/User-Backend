from __future__ import annotations

from api.user.social.views import router

app_name = "social"

urlpatterns = [
    *router.urls,
]
