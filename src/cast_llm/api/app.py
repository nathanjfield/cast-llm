"""FastAPI app for cast-llm automation endpoints."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from cast_llm.api.schemas import WeeklyHandoverRequest, WeeklyHandoverResponse
from cast_llm.services.weekly_handover import generate_weekly_handover

app = FastAPI(title="cast-llm", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Simple health endpoint."""
    return {"status": "ok"}


@app.post("/handover/weekly", response_model=WeeklyHandoverResponse)
def weekly_handover(payload: WeeklyHandoverRequest) -> WeeklyHandoverResponse:
    """Generate a handover JSON payload for CastNet (arbitrary local window or Sunday week)."""
    try:
        result = generate_weekly_handover(
            start_local=payload.start_local,
            end_local=payload.end_local,
            week_start_local=payload.week_start_local,
            model=payload.model,
            timezone_name=payload.timezone,
            include_reports=payload.include_reports,
            context_note=payload.context_note,
            use_glossary=payload.use_glossary,
            glossary_path=payload.glossary_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WeeklyHandoverResponse(**result)


def main() -> None:
    """Run the local API server."""
    import uvicorn

    uvicorn.run("cast_llm.api.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
