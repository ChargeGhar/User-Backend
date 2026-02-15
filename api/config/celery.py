from __future__ import annotations

from os import getenv

from api.config.application import TIME_ZONE
from api.config.redis import get_redis_url

broker_url = getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = get_redis_url(getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"))

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

task_always_eager = getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
task_eager_propagates = getenv("CELERY_TASK_EAGER_PROPAGATES", "false").lower() == "true"
task_ignore_result = getenv("CELERY_TASK_IGNORE_RESULT", "false").lower() == "true"

# # Reduce debug noise in production
# worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
# worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"

timezone = TIME_ZONE
enable_utc = True
