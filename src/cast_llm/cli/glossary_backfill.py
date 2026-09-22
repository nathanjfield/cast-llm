"""One-time glossary backfill runner for shift reports."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from cast_llm.services.shift_report_glossary import (
    DEFAULT_NUM_CTX,
    extract_glossary_for_week,
    merge_glossary_entries,
    merge_glossary_patterns,
)
from cast_llm.services.weekly_handover import DEFAULT_MODEL, DEFAULT_TIMEZONE
from cast_llm.utils import get_project_root


def _iter_sunday_weeks_for_year(year: int) -> list[date]:
    first_day = date(year, 1, 1)
    start = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    weeks: list[date] = []
    cur = start
    while cur.year <= year + 1:
        week_end = cur + timedelta(days=6)
        if cur.year == year or week_end.year == year:
            weeks.append(cur)
        cur += timedelta(days=7)
    return weeks


def _parse_years(value: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in value.split(",") if chunk.strip()]
    if not years:
        msg = "At least one year is required"
        raise ValueError(msg)
    return years


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build glossary from historical shift reports")
    parser.add_argument("--years", default="2026,2025", help="Comma-separated years")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help="Plant timezone")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX, help="LLM context size")
    parser.add_argument(
        "--output-dir",
        default="artifacts/shift_glossary",
        help="Output directory relative to project root",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint and skip completed weeks",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    years = _parse_years(args.years)
    root = Path(get_project_root())
    output_dir = root / args.output_dir
    weeks_dir = output_dir / "weeks"
    glossary_path = output_dir / "glossary.json"
    checkpoint_path = output_dir / "checkpoint.json"

    glossary = _load_json(
        glossary_path,
        {
            "schema_version": 1,
            "timezone": args.timezone,
            "model": args.model,
            "entries": [],
            "patterns": [],
            "completed_weeks": [],
        },
    )
    checkpoint = _load_json(checkpoint_path, {"completed_weeks": []})
    completed_weeks = set(glossary.get("completed_weeks") or [])
    completed_weeks.update(checkpoint.get("completed_weeks") or [])

    week_starts: list[date] = []
    seen_week_starts: set[date] = set()
    for year in years:
        for week_start in _iter_sunday_weeks_for_year(year):
            if week_start in seen_week_starts:
                continue
            seen_week_starts.add(week_start)
            week_starts.append(week_start)

    for week_start in week_starts:
        week_key = week_start.isoformat()
        if args.resume and week_key in completed_weeks:
            continue

        try:
            result = extract_glossary_for_week(
                week_start,
                model=args.model,
                timezone_name=args.timezone,
                num_ctx=args.num_ctx,
            )
        except Exception as exc:  # noqa: BLE001
            _save_json(
                weeks_dir / f"{week_key}.fetch_error.json",
                {
                    "week_start_local": week_key,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            continue

        glossary["entries"] = merge_glossary_entries(
            glossary.get("entries") or [],
            result.entries,
            week_start_local=week_key,
        )
        glossary["patterns"] = merge_glossary_patterns(
            glossary.get("patterns") or [],
            result.patterns,
        )

        if result.llm_error:
            failed_list = glossary.setdefault("weeks_with_llm_errors", [])
            if week_key not in failed_list:
                failed_list.append(week_key)
                failed_list.sort()

        completed_weeks.add(week_key)
        glossary["completed_weeks"] = sorted(completed_weeks)
        glossary["last_run_id"] = result.run_id
        glossary["last_week_start_local"] = week_key

        _save_json(
            weeks_dir / f"{week_key}.json",
            {
                "week_start_local": week_key,
                "result": {
                    "window": {
                        "start_local": result.window.start_local.isoformat(),
                        "end_local": result.window.end_local.isoformat(),
                        "start_utc": result.window.start_utc.isoformat(),
                        "end_utc": result.window.end_utc.isoformat(),
                    },
                    "total_reports": result.total_reports,
                    "entries": result.entries,
                    "patterns": result.patterns,
                    "duration_ms": result.duration_ms,
                    "run_id": result.run_id,
                    "llm_error": result.llm_error,
                },
            },
        )
        _save_json(glossary_path, glossary)
        _save_json(
            checkpoint_path,
            {
                "completed_weeks": sorted(completed_weeks),
                "last_week_start_local": week_key,
                "last_run_id": result.run_id,
            },
        )

    print(f"Glossary entries: {len(glossary.get('entries') or [])}")
    print(f"Patterns: {len(glossary.get('patterns') or [])}")
    print(f"Completed weeks: {len(glossary.get('completed_weeks') or [])}")


if __name__ == "__main__":
    main()
