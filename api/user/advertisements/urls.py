"""
Advertisement URLs
=================
URL routing for user advertisement endpoints
"""
from django.urls import path, include
from api.user.advertisements.views import router

app_name = 'advertisements'

urlpatterns = [
    path('', include(router.urls)),
]
