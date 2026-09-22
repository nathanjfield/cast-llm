"""Tests for plant glossary handover context."""

from __future__ import annotations

import json
from pathlib import Path

from cast_llm.glossary_context import (
    build_handover_context_note,
    format_glossary_context_note,
    load_glossary_entries,
)


def test_format_glossary_context_note() -> None:
    text = format_glossary_context_note(
        [
            {
                "term": "FH",
                "expansion": "Fixed Half",
                "definition": "Die half reference.",
            }
        ]
    )
    assert "## Plant glossary" in text
    assert "**FH**" in text
    assert "Fixed Half" in text


def test_build_handover_context_note_merges_glossary_and_note(tmp_path: Path) -> None:
    glossary = tmp_path / "glossary.json"
    glossary.write_text(
        json.dumps({"entries": [{"term": "CMM", "expansion": "Coordinate Measuring Machine"}]}),
        encoding="utf-8",
    )
    merged = build_handover_context_note(
        context_note="Wednesday 6am handover",
        glossary_path=glossary,
        use_glossary=True,
    )
    assert merged is not None
    assert "Plant glossary" in merged
    assert "CMM" in merged
    assert "Wednesday 6am handover" in merged


def test_build_handover_context_note_uses_finalglossary_when_present() -> None:
    merged = build_handover_context_note(use_glossary=True)
    assert merged is not None
    assert "Plant glossary" in merged
    entries = load_glossary_entries("artifacts/shift_glossary/finalglossary.json")
    assert len(entries) >= 1
