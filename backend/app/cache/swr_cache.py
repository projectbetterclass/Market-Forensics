"""Stale-While-Revalidate cache implementation."""

import asyncio
import time
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""
    value: Any
    last_refresh: float
    is_refreshing: bool = False


class SWRCache:
    """
    Stale-While-Revalidate cache.
    
    Returns cached data immediately if available, and refreshes in the background
    if the data is older than the refresh interval.
    """
    
    def __init__(self, refresh_interval_seconds: int = 60):
        self.refresh_interval = refresh_interval_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
    
    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Get cached value or fetch if not cached.
        
        If cached but stale, return cached immediately and refresh in background.
        """
        now = time.time()
        
        # Get or create lock for this key
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        lock = self._locks[key]
        
        # Check cache
        if key in self._cache:
            entry = self._cache[key]
            age = now - entry.last_refresh
            
            if age < self.refresh_interval:
                # Fresh data, return immediately
                return entry.value
            
            # Stale data: return it but trigger background refresh
            if not entry.is_refreshing:
                entry.is_refreshing = True
                asyncio.create_task(self._background_refresh(key, fetch_fn, args, kwargs))
            
            return entry.value
        
        # No cache: fetch now (with lock to prevent thundering herd)
        async with lock:
            # Double-check after acquiring lock
            if key in self._cache:
                return self._cache[key].value
            
            value = await fetch_fn(*args, **kwargs)
            self._cache[key] = CacheEntry(value=value, last_refresh=now)
            return value
    
    async def _background_refresh(
        self,
        key: str,
        fetch_fn: Callable,
        args: tuple,
        kwargs: dict
    ):
        """Refresh cache entry in the background."""
        try:
            value = await fetch_fn(*args, **kwargs)
            self._cache[key] = CacheEntry(value=value, last_refresh=time.time())
        except Exception as e:
            # Keep stale data on error
            print(f"Background refresh failed for {key}: {e}")
        finally:
            if key in self._cache:
                self._cache[key].is_refreshing = False
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        now = time.time()
        entries = len(self._cache)
        fresh = sum(1 for e in self._cache.values() if (now - e.last_refresh) < self.refresh_interval)
        stale = entries - fresh
        
        return {
            "total_entries": entries,
            "fresh": fresh,
            "stale": stale,
            "refresh_interval_seconds": self.refresh_interval
        }
    
    def clear(self):
        """Clear the cache."""
        self._cache.clear()
        self._locks.clear()
