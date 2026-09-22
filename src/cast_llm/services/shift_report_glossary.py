"""Glossary extraction services for historical shift reports."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from ollama import chat

from cast_llm.mongo_reports import fetch_reports_date_range, group_by_equipment
from cast_llm.services.weekly_handover import (
    DEFAULT_MODEL,
    DEFAULT_TIMEZONE,
    HandoverWindow,
    build_weekly_window,
)
from cast_llm.utils import get_project_root

DEFAULT_NUM_CTX = 128000
MAX_EVIDENCE_SNIPPETS = 5

_ABBREV_LINE_PATTERN = re.compile(
    r"\b([A-Z][A-Z0-9]{1,10})\s*(?:=|:|-)\s*([A-Za-z][A-Za-z0-9 /-]{2,80})"
)
_PARENS_PATTERN = re.compile(
    r"\b([A-Z][A-Z0-9]{1,10})\s*\(\s*([A-Za-z][A-Za-z0-9 /-]{2,80})\s*\)"
)


@dataclass(frozen=True)
class GlossaryExtractionResult:
    """Extraction payload for one weekly window."""

    window: HandoverWindow
    total_reports: int
    entries: list[dict[str, Any]]
    patterns: list[dict[str, Any]]
    duration_ms: int
    run_id: str
    llm_error: str | None = None


def load_glossary_system_prompt() -> str:
    """Load glossary extraction prompt from prompts directory."""
    prompt_path = Path(get_project_root()) / "prompts" / "shift_report_glossary_system.md"
    return prompt_path.read_text(encoding="utf-8")


def _extract_json_block(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        msg = "LLM response did not contain JSON object"
        raise ValueError(msg)
    return text[start : end + 1]


def _parse_glossary_payload(blob: str) -> dict[str, Any]:
    """Parse JSON object; raises json.JSONDecodeError if invalid."""
    parsed: Any = json.loads(blob)
    if not isinstance(parsed, dict):
        msg = "LLM JSON root must be an object"
        raise ValueError(msg)
    return parsed


def _repair_json_via_llm(
    *,
    model: str,
    num_ctx: int,
    malformed_blob: str,
    attempt: int,
) -> str:
    """Ask the model to return valid JSON only (single response, Ollama JSON mode)."""
    truncated = malformed_blob
    max_chars = 48_000
    if len(truncated) > max_chars:
        truncated = truncated[:max_chars] + "\n\n[TRUNCATED_FOR_REPAIR]"

    strictness = (
        "Return a single JSON object with exactly keys `entries` and `patterns` "
        "(arrays). Preserve as much content as possible. Use null for unknown fields."
    )
    if attempt >= 2:
        strictness = (
            "Return ONLY valid JSON. The input may be truncated or broken. "
            "Return {\"entries\":[],\"patterns\":[]} if nothing can be salvaged."
        )

    response = chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You repair JSON. Output must be a single JSON object, no markdown, "
                    "no commentary. " + strictness
                ),
            },
            {
                "role": "user",
                "content": "Fix this into valid JSON:\n\n" + truncated,
            },
        ],
        stream=False,
        format="json",
        keep_alive=-1,
        options={"num_ctx": num_ctx},
    )
    raw = str(response.message.content or "")
    return _extract_json_block(raw)


def _safe_float(value: Any, fallback: float = 0.5) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, number))


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    term = str(entry.get("term") or "").strip()
    canonical = str(entry.get("canonical_term") or term).strip() or term
    evidence = entry.get("evidence_snippets") or []
    evidence_list = [str(s).strip() for s in evidence if str(s).strip()][:MAX_EVIDENCE_SNIPPETS]
    kind = str(entry.get("kind") or "process_term").strip()
    return {
        "term": term,
        "canonical_term": canonical,
        "kind": kind,
        "expansion": entry.get("expansion"),
        "definition": str(entry.get("definition") or "").strip(),
        "confidence": _safe_float(entry.get("confidence"), 0.5),
        "evidence_snippets": evidence_list,
        "notes": str(entry.get("notes") or "").strip() or None,
    }


def _normalize_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    evidence = pattern.get("evidence_snippets") or []
    evidence_list = [str(s).strip() for s in evidence if str(s).strip()][:MAX_EVIDENCE_SNIPPETS]
    return {
        "name": str(pattern.get("name") or "").strip(),
        "description": str(pattern.get("description") or "").strip(),
        "evidence_snippets": evidence_list,
    }


def extract_deterministic_candidates(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract obvious abbreviation-expansion pairs from report text."""
    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    for row in reports:
        text = str(row.get("report") or "").strip()
        if not text:
            continue

        for pattern in (_ABBREV_LINE_PATTERN, _PARENS_PATTERN):
            for match in pattern.finditer(text):
                term = match.group(1).strip().upper()
                expansion = match.group(2).strip(" .")
                key = ("abbreviation", term)
                existing = candidates.get(key)
                if existing is None:
                    candidates[key] = {
                        "term": term,
                        "canonical_term": term,
                        "kind": "abbreviation",
                        "expansion": expansion,
                        "definition": "",
                        "confidence": 0.8,
                        "evidence_snippets": [match.group(0)],
                        "notes": "Deterministic pattern match",
                    }
                elif match.group(0) not in existing["evidence_snippets"]:
                    existing["evidence_snippets"].append(match.group(0))

    return list(candidates.values())


def _build_user_content(
    *,
    window: HandoverWindow,
    timezone_name: str,
    reports: list[dict[str, Any]],
    deterministic_candidates: list[dict[str, Any]],
    equipment_scope: str | None = None,
) -> str:
    grouped = group_by_equipment(reports)
    payload: dict[str, Any] = {
        "window": {
            "start_local": window.start_local.isoformat(),
            "end_local": window.end_local.isoformat(),
            "start_utc": window.start_utc.isoformat(),
            "end_utc": window.end_utc.isoformat(),
            "timezone": timezone_name,
        },
        "report_count": len(reports),
        "equipment_breakdown": {k: len(v) for k, v in grouped.items()},
        "deterministic_candidates": deterministic_candidates,
        "reports": reports,
    }
    if equipment_scope is not None:
        payload["equipment_scope"] = equipment_scope
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _parsed_to_entries_patterns(parsed: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize LLM payload into entry and pattern lists."""
    entries = [
        _normalize_entry(x)
        for x in parsed.get("entries", [])
        if isinstance(x, dict) and str(x.get("term") or "").strip()
    ]
    patterns = [
        _normalize_pattern(x)
        for x in parsed.get("patterns", [])
        if isinstance(x, dict) and str(x.get("name") or "").strip()
    ]
    return entries, patterns


def _parse_glossary_with_repairs(*, model: str, num_ctx: int, json_blob: str) -> dict[str, Any]:
    """Parse glossary JSON; on failure run up to three JSON-mode repair passes."""
    try:
        return _parse_glossary_payload(json_blob)
    except (json.JSONDecodeError, ValueError):
        blob = json_blob
        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                blob = _repair_json_via_llm(
                    model=model,
                    num_ctx=num_ctx,
                    malformed_blob=blob,
                    attempt=attempt,
                )
                return _parse_glossary_payload(blob)
            except (json.JSONDecodeError, ValueError) as exc:
                last_exc = exc
                continue
        if last_exc is not None:
            raise last_exc
        msg = "JSON repair failed with no exception detail"
        raise ValueError(msg)


def _call_llm_glossary_parse(
    *,
    model: str,
    num_ctx: int,
    system_prompt: str,
    user_content: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Single LLM call with JSON mode, then parse with repair fallback."""
    response = chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        stream=False,
        format="json",
        keep_alive=-1,
        options={"num_ctx": num_ctx},
    )
    raw_response = str(response.message.content or "")
    json_blob = _extract_json_block(raw_response)
    parsed = _parse_glossary_with_repairs(model=model, num_ctx=num_ctx, json_blob=json_blob)
    return _parsed_to_entries_patterns(parsed)


def _extract_with_llm_by_equipment(
    *,
    model: str,
    num_ctx: int,
    system_prompt: str,
    window: HandoverWindow,
    timezone_name: str,
    reports: list[dict[str, Any]],
    week_start_iso: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split by equipment so each LLM response stays smaller and more valid."""
    by_equipment = group_by_equipment(reports)
    merged_entries: list[dict[str, Any]] = []
    merged_patterns: list[dict[str, Any]] = []

    def _equip_sort_key(label: str) -> tuple[int, str]:
        return (0 if label else 1, label.upper())

    for equipment in sorted(by_equipment.keys(), key=_equip_sort_key):
        subset = by_equipment[equipment]
        if not subset:
            continue
        deterministic = extract_deterministic_candidates(subset)
        user_content = _build_user_content(
            window=window,
            timezone_name=timezone_name,
            reports=subset,
            deterministic_candidates=deterministic,
            equipment_scope=equipment or "Unknown",
        )
        entries, patterns = _call_llm_glossary_parse(
            model=model,
            num_ctx=num_ctx,
            system_prompt=system_prompt,
            user_content=user_content,
        )
        merged_entries = merge_glossary_entries(
            merged_entries,
            entries,
            week_start_local=week_start_iso,
        )
        merged_patterns = merge_glossary_patterns(merged_patterns, patterns)

    return merged_entries, merged_patterns


def _extract_glossary_llm_resilient(
    *,
    model: str,
    num_ctx: int,
    system_prompt: str,
    window: HandoverWindow,
    timezone_name: str,
    reports: list[dict[str, Any]],
    deterministic_candidates: list[dict[str, Any]],
    week_start_iso: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Try one full-week JSON call; on parse failure optionally split by equipment."""
    user_content = _build_user_content(
        window=window,
        timezone_name=timezone_name,
        reports=reports,
        deterministic_candidates=deterministic_candidates,
    )
    try:
        return _call_llm_glossary_parse(
            model=model,
            num_ctx=num_ctx,
            system_prompt=system_prompt,
            user_content=user_content,
        )
    except Exception as exc:
        if len(reports) < 15:
            raise
        try:
            return _extract_with_llm_by_equipment(
                model=model,
                num_ctx=num_ctx,
                system_prompt=system_prompt,
                window=window,
                timezone_name=timezone_name,
                reports=reports,
                week_start_iso=week_start_iso,
            )
        except Exception as exc2:
            raise exc2 from exc


def merge_glossary_entries(
    existing: list[dict[str, Any]],
    new_entries: list[dict[str, Any]],
    *,
    week_start_local: str,
) -> list[dict[str, Any]]:
    """Merge entries by (kind, canonical_term) while accumulating evidence."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in existing:
        key = (
            str(entry.get("kind") or "").strip().lower(),
            str(entry.get("canonical_term") or entry.get("term") or "").strip().lower(),
        )
        if key[1]:
            merged[key] = dict(entry)

    for entry in new_entries:
        canonical = str(entry.get("canonical_term") or entry.get("term") or "").strip()
        kind = str(entry.get("kind") or "").strip().lower()
        if not canonical:
            continue
        key = (kind, canonical.lower())
        target = merged.get(key)
        if target is None:
            clone = dict(entry)
            clone["seen_weeks"] = [week_start_local]
            clone["seen_count"] = 1
            merged[key] = clone
            continue

        target["seen_count"] = int(target.get("seen_count") or 1) + 1
        seen_weeks = list(target.get("seen_weeks") or [])
        if week_start_local not in seen_weeks:
            seen_weeks.append(week_start_local)
        target["seen_weeks"] = sorted(seen_weeks)

        if not target.get("expansion") and entry.get("expansion"):
            target["expansion"] = entry.get("expansion")
        if not target.get("definition") and entry.get("definition"):
            target["definition"] = entry.get("definition")

        target["confidence"] = max(
            _safe_float(target.get("confidence"), 0.0),
            _safe_float(entry.get("confidence"), 0.0),
        )

        evidence = list(target.get("evidence_snippets") or [])
        for snippet in entry.get("evidence_snippets") or []:
            if snippet and snippet not in evidence:
                evidence.append(snippet)
        target["evidence_snippets"] = evidence[:MAX_EVIDENCE_SNIPPETS]

    return sorted(
        merged.values(),
        key=lambda x: (
            str(x.get("kind") or ""),
            str(x.get("canonical_term") or x.get("term") or "").lower(),
        ),
    )


def merge_glossary_patterns(
    existing: list[dict[str, Any]],
    new_patterns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge recurring patterns by normalized pattern name."""
    merged: dict[str, dict[str, Any]] = {}
    for pattern in existing:
        name = str(pattern.get("name") or "").strip()
        if name:
            merged[name.lower()] = dict(pattern)

    for pattern in new_patterns:
        name = str(pattern.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        target = merged.get(key)
        if target is None:
            merged[key] = dict(pattern)
            continue
        if not target.get("description") and pattern.get("description"):
            target["description"] = pattern.get("description")
        evidence = list(target.get("evidence_snippets") or [])
        for snippet in pattern.get("evidence_snippets") or []:
            if snippet and snippet not in evidence:
                evidence.append(snippet)
        target["evidence_snippets"] = evidence[:MAX_EVIDENCE_SNIPPETS]
    return sorted(merged.values(), key=lambda x: str(x.get("name") or "").lower())


def extract_glossary_for_week(
    week_start_local: date,
    *,
    model: str = DEFAULT_MODEL,
    timezone_name: str = DEFAULT_TIMEZONE,
    num_ctx: int = DEFAULT_NUM_CTX,
) -> GlossaryExtractionResult:
    """Extract glossary entries for a single week window."""
    started = time.time()
    run_id = str(uuid.uuid4())
    window = build_weekly_window(week_start_local, timezone_name=timezone_name)
    reports = fetch_reports_date_range(window.start_utc, window.end_utc)
    deterministic_candidates = extract_deterministic_candidates(reports)
    system_prompt = load_glossary_system_prompt()

    llm_entries: list[dict[str, Any]] = []
    llm_patterns: list[dict[str, Any]] = []
    llm_error: str | None = None
    if reports:
        try:
            llm_entries, llm_patterns = _extract_glossary_llm_resilient(
                model=model,
                num_ctx=num_ctx,
                system_prompt=system_prompt,
                window=window,
                timezone_name=timezone_name,
                reports=reports,
                deterministic_candidates=deterministic_candidates,
                week_start_iso=week_start_local.isoformat(),
            )
        except Exception as exc:  # noqa: BLE001
            llm_error = f"{type(exc).__name__}: {exc}"

    entries = merge_glossary_entries(
        deterministic_candidates, llm_entries, week_start_local=week_start_local.isoformat()
    )
    elapsed_ms = int((time.time() - started) * 1000)
    return GlossaryExtractionResult(
        window=window,
        total_reports=len(reports),
        entries=entries,
        patterns=llm_patterns,
        duration_ms=elapsed_ms,
        run_id=run_id,
        llm_error=llm_error,
    )
