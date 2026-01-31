"""
Franchise Dashboard URLs

Base path: /api/partner/franchise/
"""

from api.partners.franchise.views import router

urlpatterns = [
    *router.urls,
]
