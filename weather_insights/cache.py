"""Simple file-based cache for API responses.

Each cached response is stored as a JSON file under the cache directory,
keyed by a hash of the request URL + sorted query parameters. Entries older
than TTL_SECONDS are treated as misses and refetched.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "weather-insights"
TTL_SECONDS = 60 * 60  # 1 hour


class Cache:
    """A minimal file-based cache keyed by request URL + params."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: int = TTL_SECONDS):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.ttl_seconds = ttl_seconds

    def _key(self, url: str, params: dict) -> str:
        normalized = json.dumps({"url": url, "params": params}, sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _path_for(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, url: str, params: dict) -> Optional[Any]:
        """Return cached JSON payload for (url, params), or None on miss/expiry."""
        path = self._path_for(self._key(url, params))
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                envelope = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return None

        stored_at = envelope.get("_cached_at", 0)
        if time.time() - stored_at > self.ttl_seconds:
            return None
        return envelope.get("data")

    def set(self, url: str, params: dict, data: Any) -> None:
        """Store JSON-serializable data under the (url, params) cache key."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        key = self._key(url, params)
        path = self._path_for(key)
        envelope = {"_cached_at": time.time(), "data": data}
        with path.open("w", encoding="utf-8") as fh:
            json.dump(envelope, fh)

    def clear(self) -> int:
        """Delete all cached entries. Returns the number of files removed."""
        if not self.cache_dir.exists():
            return 0
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count
