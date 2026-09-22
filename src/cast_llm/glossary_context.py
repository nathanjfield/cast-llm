"""Load and format plant glossary text for weekly handover context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cast_llm.utils import get_project_root

DEFAULT_HANDOVER_GLOSSARY_REL = "artifacts/shift_glossary/finalglossary.json"


def resolve_glossary_path(path: str | Path | None) -> Path | None:
    """Resolve glossary path relative to project root when not absolute."""
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(get_project_root()) / candidate
    return candidate


def load_glossary_entries(path: str | Path) -> list[dict[str, Any]]:
    """Load glossary entries from a JSON file (``entries`` array at top level)."""
    resolved = resolve_glossary_path(path)
    if resolved is None:
        msg = "glossary path is required"
        raise ValueError(msg)
    if not resolved.is_file():
        msg = f"Glossary file not found: {resolved}"
        raise FileNotFoundError(msg)

    payload = json.loads(resolved.read_text(encoding="utf-8"))
    raw = payload.get("entries")
    if not isinstance(raw, list):
        msg = f"Glossary file must contain an 'entries' array: {resolved}"
        raise ValueError(msg)
    return [e for e in raw if isinstance(e, dict)]


def format_glossary_context_note(entries: list[dict[str, Any]]) -> str:
    """Format term, expansion, and definition for handover ``context_note``."""
    lines: list[str] = []
    for entry in entries:
        term = str(entry.get("term") or entry.get("canonical_term") or "").strip()
        if not term:
            continue
        expansion = str(entry.get("expansion") or "").strip()
        definition = str(entry.get("definition") or "").strip()
        if expansion and definition:
            lines.append(f"- **{term}**: {expansion}. {definition}")
        elif expansion:
            lines.append(f"- **{term}**: {expansion}")
        elif definition:
            lines.append(f"- **{term}**: {definition}")
        else:
            lines.append(f"- **{term}**")

    if not lines:
        return ""

    header = (
        "## Plant glossary\n\n"
        "Use these definitions when abbreviations or plant terms appear in the reports. "
        "Do not invent expansions beyond this list unless clearly stated in the reports.\n\n"
    )
    return header + "\n".join(lines)


def build_handover_context_note(
    *,
    context_note: str | None = None,
    glossary_path: str | Path | None = None,
    use_glossary: bool = True,
    default_glossary_rel: str = DEFAULT_HANDOVER_GLOSSARY_REL,
) -> str | None:
    """Merge optional requester note with plant glossary text for the handover prompt."""
    parts: list[str] = []

    if use_glossary:
        rel = glossary_path if glossary_path is not None else default_glossary_rel
        resolved = resolve_glossary_path(rel)
        if resolved is not None and resolved.is_file():
            entries = load_glossary_entries(resolved)
            glossary_block = format_glossary_context_note(entries)
            if glossary_block:
                parts.append(glossary_block)

    extra = (context_note or "").strip()
    if extra:
        parts.append(extra)

    if not parts:
        return None
    return "\n\n".join(parts)
