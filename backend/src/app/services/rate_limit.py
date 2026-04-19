""" Данный модуль реализует ограничитель частоты запросов (Rate Limiter) 
    на основе алгоритма «скользящего окна» (Sliding Window). Он обеспечивает асинхронный контроль нагрузки, 
    предотвращая превышение заданного лимита событий 
    определенный интервал времени с использованием библиотеки anyio"""

import time
from collections import deque

import anyio


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float = 1.0) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: deque[float] = deque()
        self._lock = anyio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()

                while self._events and now - self._events[0] >= self.window_seconds:
                    self._events.popleft()

                if len(self._events) < self.limit:#ограничение на количество запросов к pubchem
                    self._events.append(now)
                    return

                wait_for = self.window_seconds - (now - self._events[0])

            await anyio.sleep(max(wait_for, 0.01))

