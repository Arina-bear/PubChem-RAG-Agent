import time
from collections.abc import Callable
from typing import TypeVar

import anyio

T = TypeVar("T")

class TTLCache:
    def __init__(self, max_size: int = 10000) -> None:
        self._lock = anyio.Lock()
        self._store: dict[str, tuple[float, object]] = {}
        self._max_size = max_size

    async def get(self, key: str) -> object | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            
            expires_at, value = entry
#удаление неактуальных данных
            if expires_at < time.monotonic():
                self._store.pop(key, None)
                return None
            
            return value

    async def set(self, key: str, value: object, ttl_seconds: float) -> None:
        async with self._lock:
            #контроль размера кэша(можно сделать по времени)(LRU)
            if len(self._store) >= self._max_size:
                oldest_key = next(iter(self._store))
                self._store.pop(oldest_key)

            self._store[key] = (time.monotonic() + ttl_seconds, value)

    async def get_or_set(self, key: str, ttl_seconds: float, factory: Callable[[], T]) -> T:
        cached = await self.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        value = factory()#ДОБАВИТЬ АСИНХРОН,ЧТОБЫ ИЗБЕЖАТЬ БОЛЬШОЕ КОЛИЧЕСТВО ОДИНАКОВЫХ ЗАПРОСОВ К API
        await self.set(key, value, ttl_seconds)
        return value

