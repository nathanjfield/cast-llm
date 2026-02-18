"""Filters for the cast-llm package."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .utils import get_project_root

SUPPORTED_FIELDS = {
    "name",
    "department",
    "shift",
    "equipment",
    "die",
    "cavity",
    "report",
    "date_iso",
}


def _normalize_filter_values(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, list):
        return values
    return [values]


def _extract_year(date_value: Any) -> int | None:
    if isinstance(date_value, dict):
        date_value = date_value.get("$date")
    if isinstance(date_value, int | float):
        try:
            return datetime.fromtimestamp(date_value / 1000, tz=timezone.utc).year
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(date_value, str):
        try:
            normalized = date_value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).year
        except ValueError:
            return None
    return None


def _load_filters_config(filters_config_path: str | Path | None) -> dict[str, Any]:
    if filters_config_path is None:
        filters_config_path = get_project_root() / "config" / "filters.json"
    config_path = Path(filters_config_path)
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def filter_reports_by_config(
    dict_list: list[dict[str, Any]],
    filters_config: dict[str, Any] | None = None,
    filters_config_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Filters report dictionaries by field-specific keyword configuration.

    Only fields in `SUPPORTED_FIELDS` are evaluated. Each field in the config
    must match for a report to be included. For string fields, every keyword in
    the config list must appear in that field (case-insensitive). The `date_iso`
    field expects a list of years; reports match if the date_iso year is in the
    list.

    Args:
        dict_list: A list of report dictionaries to filter.
        filters_config: Optional filter configuration dict. When omitted, the
            config is loaded from `filters_config_path`.
        filters_config_path: Path to a JSON filter config file. Defaults to
            `config/filters.json` at the project root.

    Returns:
        A new list containing only the dictionaries that match the filter criteria.
    """
    if filters_config is None:
        filters_config = _load_filters_config(filters_config_path)

    normalized_config: dict[str, list[Any]] = {
        field: _normalize_filter_values(values)
        for field, values in filters_config.items()
        if field in SUPPORTED_FIELDS
    }

    if not normalized_config:
        return list(dict_list)

    filtered_list: list[dict[str, Any]] = []

    for item in dict_list:
        matches_all_fields = True
        for field, filter_values in normalized_config.items():
            if field == "date_iso":
                allowed_years = {
                    int(year) for year in filter_values if year is not None
                }
                report_year = _extract_year(item.get("date_iso"))
                if report_year is None or report_year not in allowed_years:
                    matches_all_fields = False
                    break
                continue

            field_value = item.get(field, "")
            field_text = str(field_value).lower()
            if not all(str(keyword).lower() in field_text for keyword in filter_values):
                matches_all_fields = False
                break

        if matches_all_fields:
            filtered_list.append(item)

    return filtered_list
