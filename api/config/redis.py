from __future__ import annotations

from os import getenv
from urllib.parse import quote


def get_redis_url(
    redis_url: str | None = None, default: str = "redis://localhost:6379/0"
) -> str:
    """
    Return Redis URL with password injected when REDIS_PASSWORD is set.

    Password is URL-encoded so special characters (e.g. !, @, #) do not break parsing.
    If URL already contains credentials, it is returned unchanged.
    """
    redis_url = redis_url or getenv("REDIS_URL", default)
    redis_password = getenv("REDIS_PASSWORD", "")

    if not redis_password or "@" in redis_url:
        return redis_url

    encoded_password = quote(redis_password, safe="")

    if redis_url.startswith("redis://"):
        return redis_url.replace("redis://", f"redis://:{encoded_password}@", 1)
    if redis_url.startswith("rediss://"):
        return redis_url.replace("rediss://", f"rediss://:{encoded_password}@", 1)
    return redis_url
