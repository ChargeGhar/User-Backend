"""
Admin URLs
=========
URL routing for admin endpoints
"""
from django.urls import path, include
from api.admin.views import router
from api.admin.views.discount_views import discount_router

app_name = 'admin'

urlpatterns = [
    path('', include(router.urls)),
    path('', include(discount_router.urls)),
]
