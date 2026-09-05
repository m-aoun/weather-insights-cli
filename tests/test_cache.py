"""Unit tests for the file-based cache. No network access."""
import time

import pytest

from weather_insights.cache import Cache


@pytest.fixture
def cache(tmp_path):
    return Cache(cache_dir=tmp_path / "cache", ttl_seconds=3600)


def test_cache_miss_returns_none(cache):
    assert cache.get("https://example.com/api", {"a": 1}) is None


def test_cache_set_then_get_returns_same_data(cache):
    payload = {"temperature": 21.5, "list": [1, 2, 3]}
    cache.set("https://example.com/api", {"city": "London"}, payload)

    result = cache.get("https://example.com/api", {"city": "London"})
    assert result == payload


def test_cache_key_is_sensitive_to_params(cache):
    cache.set("https://example.com/api", {"city": "London"}, {"temp": 1})
    # Different params should be a cache miss even though the URL matches.
    assert cache.get("https://example.com/api", {"city": "Paris"}) is None


def test_cache_key_is_sensitive_to_url(cache):
    cache.set("https://example.com/api-a", {"city": "London"}, {"temp": 1})
    assert cache.get("https://example.com/api-b", {"city": "London"}) is None


def test_expired_entries_are_treated_as_misses(tmp_path):
    short_cache = Cache(cache_dir=tmp_path / "cache", ttl_seconds=0)
    short_cache.set("https://example.com/api", {"city": "London"}, {"temp": 1})
    time.sleep(0.01)
    assert short_cache.get("https://example.com/api", {"city": "London"}) is None


def test_clear_removes_all_entries(cache):
    cache.set("https://example.com/api", {"city": "London"}, {"temp": 1})
    cache.set("https://example.com/api", {"city": "Paris"}, {"temp": 2})

    removed = cache.clear()

    assert removed == 2
    assert cache.get("https://example.com/api", {"city": "London"}) is None
    assert cache.get("https://example.com/api", {"city": "Paris"}) is None


def test_corrupted_cache_file_is_treated_as_miss(cache):
    cache.set("https://example.com/api", {"city": "London"}, {"temp": 1})
    # Corrupt the underlying file directly.
    key = cache._key("https://example.com/api", {"city": "London"})
    path = cache._path_for(key)
    path.write_text("not valid json{{{", encoding="utf-8")

    assert cache.get("https://example.com/api", {"city": "London"}) is None
