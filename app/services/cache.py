import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class _CacheItem:
    value: Any
    expires_at: Optional[float]  # timestamp (epoch seconds)


class InMemoryCache:
    """
    Cache simples em memória (thread-safe via lock assíncrono).

    Chave -> valor com expiração opcional por TTL.
    """

    def __init__(self, ttl_seconds: int = 0) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, _CacheItem] = {}
        self._lock = asyncio.Lock()
        self._inflight: dict[str, asyncio.Future[Any]] = {}

    def make_key(self, namespace: str, raw: str) -> str:
        return f"{namespace}:{raw}"

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                return None

            if item.expires_at is not None and time.time() > item.expires_at:
                self._store.pop(key, None)
                return None

            return item.value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        async with self._lock:
            ttl = self._ttl_seconds if ttl_seconds is None else ttl_seconds
            expires_at = time.time() + ttl if ttl and ttl > 0 else None
            self._store[key] = _CacheItem(value=value, expires_at=expires_at)

    async def get_or_compute(
        self,
        key: str,
        compute_fn,
        ttl_seconds: int | None = None,
    ) -> Any:
        """
        Implementa "single-flight" para evitar chamadas duplicadas em concorrência.

        - Se já existe no cache, retorna imediatamente.
        - Se outra coroutine já está computando a mesma chave, aguarda o resultado.
        - Caso contrário, executa `compute_fn` uma única vez e salva no cache.
        """

        # Fast-path: tenta pegar do cache.
        cached = await self.get(key)
        if cached is not None:
            return cached

        # Single-flight: se alguém já está computando, aguardamos a mesma Future.
        async with self._lock:
            # Pode ter sido preenchido entre o get() e aqui.
            item = self._store.get(key)
            if item is not None and (item.expires_at is None or time.time() <= item.expires_at):
                return item.value

            existing_future = self._inflight.get(key)
            if existing_future is None:
                future = asyncio.get_running_loop().create_future()
                self._inflight[key] = future
                is_owner = True
            else:
                future = existing_future
                is_owner = False

        if not is_owner:
            return await future

        # Owner: computa, preenche cache e resolve a Future.
        try:
            value = await compute_fn()
            await self.set(key, value, ttl_seconds=ttl_seconds)

            async with self._lock:
                f = self._inflight.pop(key, None)
                if f is not None and not f.done():
                    f.set_result(value)

            # Garante que o owner "consome" a Future (evita warning se algo der errado).
            return await future
        except Exception as e:
            async with self._lock:
                f = self._inflight.pop(key, None)
                if f is not None and not f.done():
                    f.set_exception(e)

            # Garante que a exception da Future é recuperada (evita warning).
            await future
            raise

