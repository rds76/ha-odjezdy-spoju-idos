"""Shared helpers for IDOS data structures."""

from __future__ import annotations


def validate_response(data: dict) -> None:
    """Validate returned IDOS payload."""

    if not isinstance(data, dict):
        raise ValueError(f"Invalid response type: {type(data)}")

    for field in ("updated", "spoje"):
        if field not in data:
            raise ValueError(f"Missing field: {field}")

    if not isinstance(data["spoje"], list):
        raise ValueError("Field 'spoje' is not a list")


def first_departure_timestamp(data: dict) -> int | None:
    """Return timestamp of first departure."""

    spoje = data.get("spoje", [])

    if not spoje:
        return None

    departure = spoje[0].get("odjezd_ts")

    if departure is None:
        return None

    return int(departure)