"""Prioritize bulletin fragments so local GPU work skips low-signal edictos."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")

_HIGH_SIGNAL = (
    "contratación directa",
    "contratacion directa",
    "licitación",
    "licitacion",
    "decreto",
    "resolución",
    "resolucion",
    "subsidio",
    "transferencia",
    "adjudic",
    "fraccionamiento",
    "excepción",
    "excepcion",
    "sin licitación",
    "sin licitacion",
)

_LOW_SIGNAL = (
    "edicto",
    "se hace saber",
    "notificación",
    "notificacion",
    "remate judicial",
    "subasta judicial",
)


def fragment_priority_score(text: str) -> int:
    lowered = text.lower()
    score = 0
    for needle in _HIGH_SIGNAL:
        if needle in lowered:
            score += 3
    if "$" in text or "pesos" in lowered:
        score += 2
    for needle in _LOW_SIGNAL:
        if needle in lowered:
            score -= 2
    return score


def select_prioritized(
    items: Sequence[T],
    limit: int,
    text_of: Callable[[T], str],
) -> list[T]:
    """Keep the first item (usually the sumario) plus the highest-signal rest."""
    item_list = list(items)
    if limit <= 0 or len(item_list) <= limit:
        return item_list

    ranked = sorted(
        range(1, len(item_list)),
        key=lambda i: (-fragment_priority_score(text_of(item_list[i])), i),
    )
    keep = {0, *ranked[: limit - 1]}
    return [item for i, item in enumerate(item_list) if i in keep]
