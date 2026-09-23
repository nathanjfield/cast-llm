"""Tests for weekly handover service utilities."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from cast_llm.mongo_reports import fetch_dcm_equipment_names
from cast_llm.services.weekly_handover import (
    build_weekly_window,
    build_window_from_local_bounds,
    select_dcm_handover_equipment,
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


def test_select_dcm_handover_equipment_uses_flag_not_name_prefix() -> None:
    """Ladders and platforms are omitted unless CastNet flagged them as DCMs."""
    grouped = [
        "DCM 10",
        "DCM 2",
        "DCM Ladder 03",
        "DCM 12 Core Filling Platform",
        "Heller 1",
        "DCM 1",
    ]
    selected = select_dcm_handover_equipment(grouped, ["DCM 1", "DCM 2", "DCM 10"])
    assert selected == ["DCM 1", "DCM 2", "DCM 10"]


def test_select_dcm_handover_equipment_matches_case_and_spacing() -> None:
    """Report labels still match the registry when casing or spacing differs."""
    selected = select_dcm_handover_equipment(["dcm  1"], ["DCM 1"])
    assert selected == ["dcm  1"]


def test_fetch_dcm_equipment_names_reads_flagged_registry() -> None:
    """Only equipment documents with dcm true contribute names."""

    class _Db:
        def __getitem__(self, name: str):  # type: ignore[no-untyped-def]
            assert name == "equipment"
            return self

        def find(self, query, projection):  # type: ignore[no-untyped-def]
            assert query == {"dcm": True}
            assert projection == {"_id": 0, "equipment": 1}
            return [
                {"equipment": "DCM 1"},
                {"equipment": "  "},
                {"equipment": None},
                {"equipment": "DCM 12"},
            ]

    names = fetch_dcm_equipment_names(db=_Db())  # type: ignore[arg-type]
    assert names == {"DCM 1", "DCM 12"}
