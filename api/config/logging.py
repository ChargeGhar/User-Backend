from __future__ import annotations

import logging
from os import getenv

import colorlog

LOG_LEVEL = getenv("LOG_LEVEL", "INFO")

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        fmt="%(asctime)s %(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)

root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)
root_logger.addHandler(handler)

# ── Silence noisy third-party libraries ──
for noisy in [
    "amqp",
    "django.utils.autoreload",
    "django.template",
    "axes.apps",
    "celery.worker.consumer.mingle",
    "celery.worker.strategy",
    "kombu",
    "silk",
]:
    logging.getLogger(noisy).setLevel(logging.WARNING)