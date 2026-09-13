"""Bounded asyncio helpers for the local-hardware pipeline."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


async def map_bounded(
    items: Sequence[T] | Iterable[T],
    fn: Callable[[T], Awaitable[R]],
    limit: int,
    *,
    return_exceptions: bool = True,
) -> list[R | BaseException]:
    """Run ``fn`` over ``items`` with at most ``limit`` concurrent tasks."""
    item_list = list(items)
    if not item_list:
        return []
    sem = asyncio.Semaphore(max(1, limit))

    async def _run(item: T) -> R:
        async with sem:
            return await fn(item)

    return await asyncio.gather(
        *(_run(item) for item in item_list),
        return_exceptions=return_exceptions,
    )
