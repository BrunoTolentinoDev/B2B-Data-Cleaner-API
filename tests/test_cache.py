import asyncio

import pytest

from app.services.cache import InMemoryCache


@pytest.mark.asyncio
async def test_cache_get_or_compute_executes_once_concurrently():
    cache = InMemoryCache(ttl_seconds=60)
    key = "k1"
    calls = 0

    async def compute_fn():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)  # força concorrência
        return "value"

    results = await asyncio.gather(*[cache.get_or_compute(key, compute_fn) for _ in range(10)])
    assert results == ["value"] * 10
    assert calls == 1


@pytest.mark.asyncio
async def test_cache_ttl_expires_and_recomputes():
    cache = InMemoryCache(ttl_seconds=0)
    key = "k2"
    calls = 0

    async def compute_fn():
        nonlocal calls
        calls += 1
        return f"value-{calls}"

    v1 = await cache.get_or_compute(key, compute_fn, ttl_seconds=1)
    v2 = await cache.get_or_compute(key, compute_fn, ttl_seconds=1)
    assert v1 == v2
    assert calls == 1

    await asyncio.sleep(1.1)
    v3 = await cache.get_or_compute(key, compute_fn, ttl_seconds=1)
    assert v3 != v1
    assert calls == 2

