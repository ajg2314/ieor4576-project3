"""
LiteLLM rate-limit throttle — ported from project 2 (pipeline/orchestrator.py).

Two-layer approach:
  asyncio.Semaphore(MAX_CONCURRENT)  — at most N calls in-flight simultaneously
  asyncio.Lock + timestamp           — MIN_INTERVAL seconds between dispatches

Apply once at startup by calling apply_litellm_throttle().
Idempotent — safe to call multiple times.
"""
import asyncio
import logging
import random

import litellm

logger = logging.getLogger(__name__)

MAX_CONCURRENT_LLM_CALLS = 4
MIN_REQUEST_INTERVAL = 0.35  # seconds between successive dispatches

RATE_LIMIT_INITIAL_WAIT = 15
RATE_LIMIT_MAX_WAIT = 60

_llm_semaphore: asyncio.Semaphore | None = None
_llm_dispatch_lock: asyncio.Lock | None = None
_llm_last_dispatch: float = 0.0


def _get_throttle() -> tuple[asyncio.Semaphore, asyncio.Lock]:
    global _llm_semaphore, _llm_dispatch_lock
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)
    if _llm_dispatch_lock is None:
        _llm_dispatch_lock = asyncio.Lock()
    return _llm_semaphore, _llm_dispatch_lock


def apply_litellm_throttle() -> None:
    """Monkey-patch litellm.acompletion with semaphore + interval guard. Idempotent."""
    if getattr(litellm, "_storycoach_throttle_applied", False):
        return

    _original = litellm.acompletion

    async def _throttled(*args, **kwargs):
        global _llm_last_dispatch
        sem, lock = _get_throttle()
        async with sem:
            async with lock:
                loop = asyncio.get_running_loop()
                now = loop.time()
                gap = now - _llm_last_dispatch
                if gap < MIN_REQUEST_INTERVAL:
                    await asyncio.sleep(MIN_REQUEST_INTERVAL - gap)
                _llm_last_dispatch = loop.time()
            return await _original(*args, **kwargs)

    litellm.acompletion = _throttled
    setattr(litellm, "_storycoach_throttle_applied", True)
    logger.info(
        "LiteLLM throttle applied: max_concurrent=%d  min_interval=%.2fs",
        MAX_CONCURRENT_LLM_CALLS,
        MIN_REQUEST_INTERVAL,
    )


def is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "resource_exhausted" in msg


async def acompletion_with_retry(*args, **kwargs):
    """Call litellm.acompletion with unlimited 429 retries and capped exponential backoff."""
    attempt = 0
    while True:
        try:
            return await litellm.acompletion(*args, **kwargs)
        except Exception as exc:
            if is_rate_limit_error(exc):
                wait = min(
                    RATE_LIMIT_INITIAL_WAIT * (2 ** min(attempt, 4)) + random.uniform(0, 5),
                    RATE_LIMIT_MAX_WAIT,
                )
                logger.warning("Rate limit (attempt %d) — waiting %.0fs", attempt + 1, wait)
                await asyncio.sleep(wait)
                attempt += 1
            else:
                raise
