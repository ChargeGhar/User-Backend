from __future__ import annotations

import logging

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from api.config.silk import USE_SILK
from api.config.storage import (
    USE_S3_FOR_MEDIA,
    USE_S3_FOR_STATIC,
)

logger = logging.getLogger(__name__)

# Define error handlers
def handler400(request, exception=None):
    from rest_framework.views import exception_handler
    from rest_framework.exceptions import APIException
    from django.http import JsonResponse
    return JsonResponse({'detail': 'Bad request'}, status=400)

def handler404(request, exception=None):
    from django.http import JsonResponse
    return JsonResponse({'detail': 'Not found'}, status=404)

def handler500(request):
    from django.http import JsonResponse
    return JsonResponse({'detail': 'Internal server error'}, status=500)

_swagger_urlpatterns = [
    path(
        "api/v1/schema/",
        extend_schema(exclude=True)(SpectacularAPIView).as_view(),
        name="schema",
    ),
    path(
        "docs/",
        extend_schema(exclude=True)(SpectacularSwaggerView).as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        extend_schema(exclude=True)(SpectacularRedocView).as_view(url_name="schema"),
        name="redoc",
    ),
]

urlpatterns = [
    *_swagger_urlpatterns,
    path("", lambda _request: redirect("docs/"), name="home"),
    path("admin/", admin.site.urls),
    
    # Django Allauth URLs
    path("accounts/", include("allauth.urls")),
    
    # API app includes - User Namespace
    path("api/", include("api.user.auth.urls")),
    path("api/", include("api.user.stations.urls")),
    path("api/", include("api.internal.urls")),  # Internal IoT endpoints
    path("api/", include("api.user.notifications.urls")),
    path("api/", include("api.user.payments.urls")),
    path("api/", include("api.user.points.urls")),
    path("api/", include("api.user.rentals.urls")),
    path("api/", include("api.user.social.urls")),
    path("api/", include("api.user.promotions.urls")),
    path("api/", include("api.user.content.urls")),
    path("api/", include("api.admin.urls")),
    path("api/", include("api.user.system.urls")),
    path("api/", include("api.user.media.urls")),
    path("api/", include("api.user.advertisements.urls")),
]

if USE_SILK:
    urlpatterns.append(path("silk/", include("silk.urls")))

if not USE_S3_FOR_STATIC:
    # Force serving static files even in production mode for development
    from django.views.static import serve
    from django.urls import re_path
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]

if not USE_S3_FOR_MEDIA:
    logger.warning("S3 is disabled, serving media files locally. Consider using S3.")
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Register error handlers
from django.core.exceptions import PermissionDenied
from django.http import Http404

def handler400(request, exception=None):
    return JsonResponse({'error': 'Bad request'}, status=400)

def handler403(request, exception=None):
    return JsonResponse({'error': 'Permission denied'}, status=403)

def handler404(request, exception=None):
    return JsonResponse({'error': 'Not found'}, status=404)

def handler500(request, exception=None):
    return JsonResponse({'error': 'Internal server error'}, status=500)
