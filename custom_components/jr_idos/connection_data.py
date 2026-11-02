"""Shared helpers for IDOS data structures."""

from __future__ import annotations

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