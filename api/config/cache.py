from __future__ import annotations

import logging
from os import getenv
from typing import Any

logger = logging.getLogger(__name__)

USE_REDIS_FOR_CACHE = getenv("USE_REDIS_FOR_CACHE", default="true").lower() == "true"
REDIS_URL = getenv("REDIS_URL", default="redis://localhost:6379/0")
REDIS_PASSWORD = getenv("REDIS_PASSWORD", "")

CACHES: dict[str, Any] = {}

if USE_REDIS_FOR_CACHE:
    logger.debug("Using Redis for cache")
    CACHES["default"] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            **({"PASSWORD": REDIS_PASSWORD} if REDIS_PASSWORD else {}),
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
