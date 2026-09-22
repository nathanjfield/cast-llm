"""Weekly handover generation service."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ollama import chat

from cast_llm.glossary_context import build_handover_context_note
from cast_llm.mongo_reports import fetch_reports_date_range, group_by_equipment
from cast_llm.settings import get_settings
from cast_llm.utils import get_project_root

DEFAULT_MODEL = "gemma4:latest"
DEFAULT_TIMEZONE = "Europe/London"


@dataclass(frozen=True)
class HandoverWindow:
    """Date/time boundaries for a handover query (Mongo `date_iso` in UTC)."""

    start_local: datetime
    end_local: datetime
    start_utc: datetime
    end_utc: datetime


def _require_tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:  # pragma: no cover
        msg = f"Invalid timezone: {name!r}"
        raise ValueError(msg) from exc


def _attach_or_convert_local(
    value: datetime,
    plant_tz: ZoneInfo,
) -> datetime:
    """Interpret naive as plant wall time, or convert aware instant to plant tz for display."""
    if value.tzinfo is None:
        return value.replace(tzinfo=plant_tz)
    return value.astimezone(plant_tz)


def build_window_from_local_bounds(
    start_local: datetime,
    end_local: datetime,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> HandoverWindow:
    """Build UTC bounds from inclusive local start/end datetimes (plant timezone for naive)."""
    plant = _require_tz(timezone_name)
    start = _attach_or_convert_local(start_local, plant)
    end = _attach_or_convert_local(end_local, plant)
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    if end_utc < start_utc:
        msg = "end_local must be on or after start_local"
        raise ValueError(msg)
    return HandoverWindow(
        start_local=start,
        end_local=end,
        start_utc=start_utc,
        end_utc=end_utc,
    )


def build_weekly_window(
    week_start_local: date,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> HandoverWindow:
    """Build local and UTC boundaries for a Sunday 00:00 to Saturday 23:59:59 (inclusive) week."""
    local_tz = _require_tz(timezone_name)
    start = datetime.combine(week_start_local, dt_time.min, tzinfo=local_tz)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return build_window_from_local_bounds(
        start,
        end,
        timezone_name=timezone_name,
    )


def load_weekly_system_prompt() -> str:
    """Load the weekly handover system prompt from prompts directory."""
    prompt_path = Path(get_project_root()) / "prompts" / "weekly_handover_system.md"
    return prompt_path.read_text(encoding="utf-8")


def _is_dcm_equipment(name: str) -> bool:
    """Return true for equipment labels starting with DCM."""
    return name.strip().upper().startswith("DCM")


def _dcm_numeric_sort_key(name: str) -> tuple[int, str]:
    """Sort DCM 1, DCM 2, ..., DCM 10 in numeric order."""
    match = re.search(r"DCM\s*(\d+)", name.strip(), flags=re.IGNORECASE)
    if match:
        return (int(match.group(1)), name)
    return (10**9, name)


def generate_weekly_handover(
    *,
    start_local: datetime | None = None,
    end_local: datetime | None = None,
    week_start_local: date | None = None,
    model: str = DEFAULT_MODEL,
    timezone_name: str = DEFAULT_TIMEZONE,
    num_ctx: int = 128000,
    include_reports: bool = False,
    context_note: str | None = None,
    use_glossary: bool | None = None,
    glossary_path: str | None = None,
) -> dict[str, Any]:
    """Generate DCM handover summaries for an arbitrary or calendar-week local window.

    Pass either:

    * ``start_local`` and ``end_local`` (inclusive window; naive times use ``timezone_name``), or
    * ``week_start_local`` (Sunday) for a full UK calendar week.
    """
    if (start_local is None) ^ (end_local is None):
        msg = "Provide both start_local and end_local, or use week_start_local only"
        raise ValueError(msg)
    if start_local is not None and end_local is not None:
        window = build_window_from_local_bounds(
            start_local, end_local, timezone_name=timezone_name
        )
    elif week_start_local is not None:
        window = build_weekly_window(week_start_local, timezone_name=timezone_name)
    else:
        msg = "Provide start_local and end_local, or week_start_local"
        raise ValueError(msg)

    started = time.time()
    run_id = str(uuid.uuid4())
    system_prompt = load_weekly_system_prompt()

    settings = get_settings()
    glossary_enabled = (
        settings.handover_glossary_enabled if use_glossary is None else use_glossary
    )
    resolved_glossary_path = (
        glossary_path if glossary_path is not None else settings.handover_glossary_path
    )
    merged_context_note = build_handover_context_note(
        context_note=context_note,
        glossary_path=resolved_glossary_path,
        use_glossary=glossary_enabled,
    )

    rows = fetch_reports_date_range(window.start_utc, window.end_utc)
    by_equipment = group_by_equipment(rows)
    dcm_equipment_order = sorted(
        (name for name in by_equipment if _is_dcm_equipment(name)),
        key=_dcm_numeric_sort_key,
    )

    task_intro = (
        "Summarise for the oncoming shift on this machine only. Be brief (see system "
        "prompt). Weight the **latter part of the date range** and the **most recent** "
        "reports; de-emphasise issues only seen early in the range that were fixed and "
        "did not recur."
    )
    if merged_context_note:
        task_intro = (
            f"{task_intro}\n\n**Handover context (from the requester):** {merged_context_note}"
        )
    user_header = (
        f"## Task\n{task_intro}\n\n"
        f"## Requested range (local, {timezone_name})\n"
        f"{window.start_local.isoformat()} – {window.end_local.isoformat()}\n\n"
        f"## Range (UTC, matches Mongo `date_iso` window)\n"
        f"{window.start_utc.isoformat()} – {window.end_utc.isoformat()}\n"
        "(Use report dates for recency within the window.)\n\n"
    )

    machines: list[dict[str, Any]] = []
    for equipment in dcm_equipment_order:
        reports = by_equipment[equipment]
        user_content = (
            f"{user_header}"
            f"## equipment\n{json.dumps(equipment)}\n\n"
            f"## Shift reports (JSON array)\n{json.dumps(reports, indent=2)}"
        )

        machine_payload: dict[str, Any] = {
            "equipment": equipment,
            "report_count": len(reports),
            "summary": "",
            "error": None,
        }

        try:
            stream = chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                stream=True,
                keep_alive=-1,
                options={"num_ctx": num_ctx},
            )
            chunks: list[str] = []
            for chunk in stream:
                chunks.append(chunk["message"]["content"])
            machine_payload["summary"] = "".join(chunks)
        except Exception as exc:  # noqa: BLE001
            machine_payload["error"] = str(exc)

        if include_reports:
            machine_payload["reports"] = reports
        machines.append(machine_payload)

    elapsed_ms = int((time.time() - started) * 1000)
    return {
        "run_id": run_id,
        "model": model,
        "timezone": timezone_name,
        "start_local": window.start_local.isoformat(),
        "end_local": window.end_local.isoformat(),
        "start_utc": window.start_utc.isoformat(),
        "end_utc": window.end_utc.isoformat(),
        "total_reports": len(rows),
        "machine_count": len(machines),
        "duration_ms": elapsed_ms,
        "machines": machines,
    }
