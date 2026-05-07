"""Process-wide LLM rate limiters.

LangChain's `InMemoryRateLimiter` implements an asyncio-safe token bucket
and is consumed by every `BaseChatModel` (incl. `ChatGoogleGenerativeAI`)
through the constructor's `rate_limiter=` argument. The model awaits
`rate_limiter.aacquire()` *before* each LLM HTTP call — so a request will
park in the queue rather than fail with 429 when the bucket is empty.

We expose **one singleton per provider** so that concurrent Chainlit
sessions and the FastAPI `/api/agent` endpoint share the same global
quota inside a single Python process.

Caveats
-------
- Works only inside one process. If the deployment scales to several
  uvicorn workers, swap for a Redis-backed limiter.
- Buckets count *requests*, not tokens — Google's free tier on Gemini /
  Gemma uses RPM, which matches.
- The default of 13 RPM leaves headroom under Google's 15-RPM free-tier
  cap; it absorbs skew between the client's monotonic clock and Google's
  quota window (otherwise the last request in a minute can still hit 429).
"""
from __future__ import annotations

from langchain_core.rate_limiters import InMemoryRateLimiter

from app.config import Settings


_gemini_limiter: InMemoryRateLimiter | None = None


def get_gemini_rate_limiter(settings: Settings) -> InMemoryRateLimiter:
    """Return the singleton rate limiter shared by all Gemini/Gemma calls.

    Lazily built from ``settings.llm_rate_limit_gemini_rpm``; subsequent
    calls reuse the same instance so the token bucket is global to the
    process.
    """
    global _gemini_limiter
    if _gemini_limiter is None:
        rpm = settings.llm_rate_limit_gemini_rpm
        _gemini_limiter = InMemoryRateLimiter(
            requests_per_second=rpm / 60.0,
            check_every_n_seconds=0.1,
            max_bucket_size=float(rpm),
        )
    return _gemini_limiter
