"""
Admin URLs
=========
URL routing for admin endpoints
"""
from django.urls import path, include
from api.admin.views import router

app_name = 'admin'

urlpatterns = [
    path('admin/', include(router.urls)),
]
