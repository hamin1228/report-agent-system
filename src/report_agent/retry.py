"""Async retry helper with bounded exponential backoff."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base_delay_seconds: float,
) -> T:
    """Run an async operation with bounded exponential backoff."""

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            await asyncio.sleep(base_delay_seconds * (2**attempt))
    if last_error is None:
        raise RuntimeError("Retry operation did not execute")
    raise last_error
