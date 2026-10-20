"""Shared response helpers for the standard API envelope."""

from typing import Any


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wrap a successful payload as {"data": ..., "meta": ...}."""
    return {"data": data, "meta": meta or {}}
