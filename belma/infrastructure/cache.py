"""LRU cache for analysis results — Eq. (8) of the paper.

Caches `Cache[S] = Retrieve(S)` so iterative repair cycles don't re-analyze
identical contracts. Capability metrics are independent of this cache; only
infrastructure metrics (TP, L) benefit.
"""
from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CacheEntry:
    value: Any
    timestamp: float


@dataclass
class AnalysisCache:
    max_entries: int = 50_000
    ttl_seconds: int = 86_400
    enabled: bool = True
    _store: OrderedDict = field(default_factory=OrderedDict)

    def _key(self, source: str) -> str:
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def get(self, source: str) -> Optional[Any]:
        if not self.enabled:
            return None
        k = self._key(source)
        entry = self._store.get(k)
        if entry is None:
            return None
        if time.time() - entry.timestamp > self.ttl_seconds:
            del self._store[k]
            return None
        # LRU bump
        self._store.move_to_end(k)
        return entry.value

    def put(self, source: str, value: Any) -> None:
        if not self.enabled:
            return
        k = self._key(source)
        self._store[k] = CacheEntry(value=value, timestamp=time.time())
        self._store.move_to_end(k)
        while len(self._store) > self.max_entries:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()
