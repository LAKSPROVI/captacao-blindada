"""
Comprehensive tests for djen.api.cache module.

Tests CacheManager with TTL, cleanup, stats, and thread safety.
"""

import time
import threading
import pytest
from djen.api.cache import CacheManager, CacheItem, get_cache


# =========================================================================
# CacheItem
# =========================================================================

class TestCacheItem:
    def test_not_expired(self):
        item = CacheItem(key="k", value="v", expires_at=time.time() + 100, created_at=time.time())
        assert item.is_expired() is False

    def test_expired(self):
        item = CacheItem(key="k", value="v", expires_at=time.time() - 1, created_at=time.time())
        assert item.is_expired() is True

    def test_just_expired(self):
        item = CacheItem(key="k", value="v", expires_at=time.time() - 0.001, created_at=time.time())
        assert item.is_expired() is True


# =========================================================================
# CacheManager - Basic Operations
# =========================================================================

class TestCacheManagerBasic:
    def setup_method(self):
        self.cache = CacheManager()

    def test_set_and_get(self):
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"

    def test_get_missing_returns_default(self):
        assert self.cache.get("missing") is None
        assert self.cache.get("missing", "default") == "default"

    def test_set_overwrites(self):
        self.cache.set("key", "v1")
        self.cache.set("key", "v2")
        assert self.cache.get("key") == "v2"

    def test_delete_existing(self):
        self.cache.set("key", "val")
        assert self.cache.delete("key") is True
        assert self.cache.get("key") is None

    def test_delete_nonexistent(self):
        assert self.cache.delete("nope") is False

    def test_clear(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        assert self.cache.clear() is True
        assert self.cache.get("a") is None
        assert self.cache.get("b") is None

    def test_set_various_types(self):
        self.cache.set("str", "hello")
        self.cache.set("int", 42)
        self.cache.set("float", 3.14)
        self.cache.set("list", [1, 2, 3])
        self.cache.set("dict", {"a": 1})
        self.cache.set("bool", True)
        self.cache.set("none", None)
        assert self.cache.get("str") == "hello"
        assert self.cache.get("int") == 42
        assert self.cache.get("list") == [1, 2, 3]
        assert self.cache.get("dict") == {"a": 1}
        assert self.cache.get("none") is None  # indistinguishable from miss


# =========================================================================
# CacheManager - TTL
# =========================================================================

class TestCacheManagerTTL:
    def setup_method(self):
        self.cache = CacheManager()

    def test_expired_item_returns_default(self):
        self.cache.set("exp", "val", ttl=1)
        # Manually expire the item
        self.cache._cache["exp"].expires_at = time.time() - 1
        assert self.cache.get("exp") is None

    def test_custom_ttl(self):
        self.cache.set("short", "val", ttl=1)
        assert self.cache.get("short") == "val"

    def test_default_ttl_is_300(self):
        assert self.cache._default_ttl == 300


# =========================================================================
# CacheManager - Stats
# =========================================================================

class TestCacheManagerStats:
    def setup_method(self):
        self.cache = CacheManager()

    def test_initial_stats(self):
        stats = self.cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["items"] == 0
        assert stats["backend"] == "memory"

    def test_hit_increments(self):
        self.cache.set("k", "v")
        self.cache.get("k")
        stats = self.cache.stats()
        assert stats["hits"] == 1

    def test_miss_increments(self):
        self.cache.get("missing")
        stats = self.cache.stats()
        assert stats["misses"] == 1

    def test_hit_rate_calculation(self):
        self.cache.set("k", "v")
        self.cache.get("k")  # hit
        self.cache.get("missing")  # miss
        stats = self.cache.stats()
        assert stats["hit_rate"] == 0.5

    def test_items_count(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        stats = self.cache.stats()
        assert stats["items"] == 2


# =========================================================================
# CacheManager - Thread Safety
# =========================================================================

class TestCacheManagerThreadSafety:
    def test_concurrent_writes(self):
        cache = CacheManager()
        errors = []

        def writer(tid):
            try:
                for i in range(50):
                    cache.set(f"t{tid}_k{i}", f"v{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.stats()["items"] == 250

    def test_concurrent_reads_and_writes(self):
        cache = CacheManager()
        cache.set("shared", "initial")
        errors = []

        def reader():
            try:
                for _ in range(100):
                    cache.get("shared")
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(100):
                    cache.set("shared", f"v{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(3)]
        threads += [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =========================================================================
# CacheManager - Cleanup
# =========================================================================

class TestCacheManagerCleanup:
    def test_cleanup_removes_expired(self):
        cache = CacheManager()
        cache._max_items = 5
        # Add expired items
        for i in range(3):
            cache.set(f"exp_{i}", f"v{i}", ttl=0)
        time.sleep(0.05)
        # Add items to trigger cleanup
        for i in range(6):
            cache.set(f"new_{i}", f"v{i}")
        # Expired items should be cleaned
        assert cache.stats()["items"] <= 6


# =========================================================================
# Global singleton
# =========================================================================

class TestGetCache:
    def test_returns_cache_manager(self):
        c = get_cache()
        assert isinstance(c, CacheManager)

    def test_singleton(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2
