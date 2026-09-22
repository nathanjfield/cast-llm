"""Tests for weekly handover service utilities."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from cast_llm.services.weekly_handover import (
    build_weekly_window,
    build_window_from_local_bounds,
)


def test_build_weekly_window_uk_range() -> None:
    """Builds a full Sunday-Saturday UK window."""
    window = build_weekly_window(date(2026, 4, 12), timezone_name="Europe/London")
    assert window.start_local.isoformat() == "2026-04-12T00:00:00+01:00"
    assert window.end_local.isoformat() == "2026-04-18T23:59:59+01:00"
    assert window.start_utc.isoformat() == "2026-04-11T23:00:00+00:00"
    assert window.end_utc.isoformat() == "2026-04-18T22:59:59+00:00"


def test_build_window_wednesday_sixam_span() -> None:
    """Wednesday 6:00 to next Wednesday 6:00 in Europe/London."""
    lon = ZoneInfo("Europe/London")
    start = datetime(2026, 4, 22, 6, 0, 0, tzinfo=lon)
    end = datetime(2026, 4, 29, 6, 0, 0, tzinfo=lon)
    w = build_window_from_local_bounds(start, end, timezone_name="Europe/London")
    assert w.start_utc == start.astimezone(timezone.utc)
    assert w.end_utc == end.astimezone(timezone.utc)


def test_build_window_rejects_inverted() -> None:
    """end before start raises."""
    lon = ZoneInfo("Europe/London")
    with pytest.raises(ValueError, match="on or after"):
        build_window_from_local_bounds(
            datetime(2026, 4, 29, 6, 0, 0, tzinfo=lon),
            datetime(2026, 4, 22, 6, 0, 0, tzinfo=lon),
        )


def test_build_window_naive_uses_plant_timezone() -> None:
    """Naive datetimes are treated as local wall time in `timezone` name."""
    w = build_window_from_local_bounds(
        datetime(2026, 4, 22, 6, 0, 0),
        datetime(2026, 4, 22, 18, 0, 0),
        timezone_name="Europe/London",
    )
    assert w.start_local.tzinfo is not None
    assert (w.end_utc - w.start_utc) == timedelta(hours=12)
