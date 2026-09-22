"""Request/response schemas for weekly handover API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from cast_llm.services.weekly_handover import DEFAULT_TIMEZONE


class WeeklyHandoverRequest(BaseModel):
    """Handover trigger: either a full local window or a legacy Sunday week."""

    start_local: datetime | None = Field(
        default=None,
        description="Inclusive start of the report window in plant local time (naive uses `timezone`)",
    )
    end_local: datetime | None = Field(
        default=None,
        description="Inclusive end of the report window in plant local time (naive uses `timezone`)",
    )
    week_start_local: date | None = Field(
        default=None,
        description="If set without start/end, Sunday 00:00 to Saturday 23:59:59 in `timezone`",
    )
    timezone: str = Field(default=DEFAULT_TIMEZONE)
    model: str = Field(default="gemma4:latest")
    include_reports: bool = Field(default=False)
    context_note: str | None = Field(
        default=None,
        description="Optional note e.g. Wednesday 6am handover; appended after plant glossary",
    )
    use_glossary: bool | None = Field(
        default=None,
        description=(
            "Include plant glossary in handover context (default from "
            "CAST_LLM_HANDOVER_GLOSSARY_ENABLED, usually true)"
        ),
    )
    glossary_path: str | None = Field(
        default=None,
        description=(
            "Glossary JSON path relative to project root (default "
            "artifacts/shift_glossary/finalglossary.json)"
        ),
    )

    @model_validator(mode="after")
    def check_window(self) -> WeeklyHandoverRequest:
        """Require either (start + end) or week_start_local."""
        has_range = self.start_local is not None and self.end_local is not None
        has_week = self.week_start_local is not None
        if has_range and has_week:
            msg = "Use either (start_local, end_local) or week_start_local, not both"
            raise ValueError(msg)
        if not has_range and not has_week:
            msg = "Provide start_local and end_local, or week_start_local"
            raise ValueError(msg)
        if (self.start_local is None) ^ (self.end_local is None):
            msg = "start_local and end_local must both be set"
            raise ValueError(msg)
        return self


class MachineSummary(BaseModel):
    """One machine summary result."""

    equipment: str
    report_count: int
    summary: str
    error: str | None = None
    reports: list[dict] | None = None


class WeeklyHandoverResponse(BaseModel):
    """Weekly handover API response payload."""

    run_id: str
    model: str
    timezone: str
    start_local: str
    end_local: str
    start_utc: str
    end_utc: str
    total_reports: int
    machine_count: int
    duration_ms: int
    machines: list[MachineSummary]
