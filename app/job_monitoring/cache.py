"""A bounded, in-memory LRU-ish cache of seen job keys.

Backs `deduplication.py`'s fast-path lookup so a long-running monitor
doesn't have to re-read the full on-disk history on every duplicate
check. Bounded (`max_size`) to keep memory usage flat over an indefinite
monitoring run — the oldest key is evicted once the cache is full,
exactly like a real LRU cache, using only the stdlib.
"""

from collections import OrderedDict


class JobCache:
    def __init__(self, max_size: int = 10_000) -> None:
        self._max_size = max_size
        self._keys: OrderedDict[str, None] = OrderedDict()

    def __contains__(self, key: str) -> bool:
        return key in self._keys

    def __len__(self) -> int:
        return len(self._keys)

    def add(self, key: str) -> None:
        if key in self._keys:
            self._keys.move_to_end(key)
            return
        self._keys[key] = None
        if len(self._keys) > self._max_size:
            self._keys.popitem(last=False)

    def clear(self) -> None:
        self._keys.clear()
