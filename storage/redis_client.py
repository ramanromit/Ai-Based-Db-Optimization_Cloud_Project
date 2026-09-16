import os
import time
import json
import logging
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("caqi.storage.redis")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class MockRedisClient:
    """In-memory Redis stand-in with TTL expiration semantics."""
    def __init__(self):
        self._store = {}
        self._expires = {}

    def get(self, key: str) -> Optional[str]:
        if key in self._expires and time.time() > self._expires[key]:
            del self._store[key]
            del self._expires[key]
            return None
        return self._store.get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        if ex is not None:
            self._expires[key] = time.time() + ex
        elif key in self._expires:
            del self._expires[key]
        return True

    def delete(self, key: str) -> int:
        count = 0
        if key in self._store:
            del self._store[key]
            count += 1
        if key in self._expires:
            del self._expires[key]
        return count

    def ping(self) -> bool:
        return True

    def flushdb(self):
        self._store.clear()
        self._expires.clear()

def get_redis_client():
    """Initializes real Redis connection or falls back to MockRedisClient."""
    try:
        import redis
        client = redis.Redis.from_url(REDIS_URL, socket_timeout=1.0, decode_responses=True)
        client.ping()
        logger.info(f"Connected to Redis at {REDIS_URL}")
        return client
    except Exception as e:
        logger.warning(f"Redis unreachable ({e}). Using in-memory MockRedisClient.")
        return MockRedisClient()

redis_client = get_redis_client()

