"""Shared helpers for IDOS data structures."""

from __future__ import annotations

from datetime import datetime

from .const import (
    ATTR_ODJEZD_TS,
    ATTR_SPOJE,
    ATTR_UPDATED,
)


def validate_response(data: dict) -> None:
    """Validate returned IDOS payload."""

    if not isinstance(data, dict):
        raise ValueError(f"Invalid response type: {type(data)}")

    for field in (ATTR_UPDATED, ATTR_SPOJE):
        if field not in data:
            raise ValueError(f"Missing field: {field}")

    if not isinstance(data[ATTR_SPOJE], list):
        raise ValueError(f"Field {ATTR_SPOJE} is not a list")


def first_departure_timestamp(data: dict) -> int | None:
    """Return timestamp of first departure."""

    spoje = data.get(ATTR_SPOJE, [])

    if not spoje:
        return None

    departure = spoje[0].get(ATTR_ODJEZD_TS)

    if departure is None:
        return None

    return int(departure)

def filter_from(spoje: list[dict], search_dt: datetime) -> list[dict]:
    """
    Keep connections departing at or after the minute of search_dt.
    IDOS may also return earlier connections whose delay keeps them in the future.
    """

    min_ts = search_dt.replace(second=0, microsecond=0).timestamp()
    return [s for s in spoje if s[ATTR_ODJEZD_TS] >= min_ts]