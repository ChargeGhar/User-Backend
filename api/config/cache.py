from __future__ import annotations

import logging
from os import getenv
from typing import Any

from django.core.cache import cache
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

USE_REDIS_FOR_CACHE = getenv("USE_REDIS_FOR_CACHE", default="true").lower() == "true"
REDIS_URL = getenv("REDIS_URL", default="redis://localhost:6379/0")

CACHES: dict[str, Any] = {}

if USE_REDIS_FOR_CACHE:
    logger.debug("Using Redis for cache")
    CACHES["default"] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }

    # Don't test cache connection during startup to avoid blocking Django initialization
    # The cache will be tested when first used
    logger.debug("Redis cache configured - connection will be tested on first use")
else:
    logger.warning("Using dummy cache")
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
