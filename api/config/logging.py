from __future__ import annotations

import logging.config
from os import getenv

LOG_LEVEL = getenv("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(asctime)s %(log_color)s%(levelname)-5s%(reset)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colored",
        },
    },
    "loggers": {
        # Root logger — your app
        "": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        # ── Silence noisy third-party libraries ──
        # AMQP connection debug spam
        "amqp": {"level": "WARNING"},
        # Django internals
        "django.utils.autoreload": {"level": "WARNING"},
        "django.template": {"level": "WARNING"},
        # Axes login attempt monitoring (startup banner repeats per worker)
        "axes.apps": {"level": "WARNING"},
        # Celery internal chatter
        "celery.worker.consumer.mingle": {"level": "WARNING"},
        "celery.worker.strategy": {"level": "WARNING"},
        # Kombu/redis transport noise
        "kombu": {"level": "WARNING"},
        # Silk profiler (if enabled)
        "silk": {"level": "WARNING"},
    },
}

logging.config.dictConfig(LOGGING)
