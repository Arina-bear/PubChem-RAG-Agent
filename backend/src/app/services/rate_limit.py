""" Данный модуль реализует ограничитель частоты запросов (Rate Limiter) 
    на основе алгоритма «скользящего окна» (Sliding Window). Он обеспечивает асинхронный контроль нагрузки, 
    предотвращая превышение заданного лимита событий 
    определенный интервал времени с использованием библиотеки anyio"""

import time
from collections import deque

import anyio


class SlidingWindowRateLimiter:
    """Реализует алгоритм 'скользящего окна' для контроля интенсивности запросов.

    Этот ограничитель гарантирует, что количество событий (запросов) в любой 
    произвольный интервал времени (window_seconds) не превысит заданный лимит. 
    В отличие от алгоритма фиксированного окна, скользящее окно обеспечивает 
    более плавное распределение нагрузки и защищает от всплесков трафика 
    на границах временных интервалов.

    Attributes:
        limit (int): Максимально допустимое количество запросов в пределах окна.
        window_seconds (float): Размер временного окна в секундах (по умолчанию 1.0).
        _events (deque): Очередь временных меток последних успешно выполненных запросов.
        _lock (anyio.Lock): Асинхронный замок для обеспечения потокобезопасности 
            в многопоточной/асинхронной среде.
    """
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

