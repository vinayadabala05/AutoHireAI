"""Unit tests for `app.job_monitoring.cache.JobCache`."""

from app.job_monitoring.cache import JobCache


def test_add_and_contains() -> None:
    cache = JobCache()
    assert "a" not in cache
    cache.add("a")
    assert "a" in cache


def test_len_reflects_number_of_keys() -> None:
    cache = JobCache()
    cache.add("a")
    cache.add("b")
    assert len(cache) == 2


def test_add_existing_key_moves_it_to_most_recently_used() -> None:
    cache = JobCache(max_size=2)
    cache.add("a")
    cache.add("b")
    cache.add("a")  # re-add "a" — should not evict it next
    cache.add("c")  # forces an eviction: "b" (least recently used) should go
    assert "a" in cache
    assert "b" not in cache
    assert "c" in cache


def test_exceeding_max_size_evicts_oldest() -> None:
    cache = JobCache(max_size=2)
    cache.add("a")
    cache.add("b")
    cache.add("c")
    assert len(cache) == 2
    assert "a" not in cache
    assert "b" in cache
    assert "c" in cache


def test_clear_empties_the_cache() -> None:
    cache = JobCache()
    cache.add("a")
    cache.clear()
    assert len(cache) == 0
    assert "a" not in cache
