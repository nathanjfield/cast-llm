"""Tests for weekly handover API endpoint."""

from fastapi.testclient import TestClient

from cast_llm.api.app import app


def _fake_result() -> dict:
    return {
        "run_id": "run-1",
        "model": "gemma4:latest",
        "timezone": "Europe/London",
        "start_local": "2026-04-12T00:00:00+01:00",
        "end_local": "2026-04-18T23:59:59+01:00",
        "start_utc": "2026-04-11T23:00:00+00:00",
        "end_utc": "2026-04-18T22:59:59+00:00",
        "total_reports": 3,
        "machine_count": 1,
        "duration_ms": 123,
        "machines": [
            {
                "equipment": "DCM 1",
                "report_count": 3,
                "summary": "Ready for startup.",
                "error": None,
            }
        ],
    }


def test_weekly_handover_endpoint_week_mode(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Returns typed response from service payload (week_start_local)."""

    def _fake_generate_weekly_handover(**_: object) -> dict:
        return _fake_result()

    monkeypatch.setattr(
        "cast_llm.api.app.generate_weekly_handover",
        _fake_generate_weekly_handover,
    )

    client = TestClient(app)
    response = client.post(
        "/handover/weekly",
        json={
            "week_start_local": "2026-04-12",
            "timezone": "Europe/London",
            "model": "gemma4:latest",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-1"
    assert payload["machine_count"] == 1
    assert payload["machines"][0]["equipment"] == "DCM 1"
    assert "start_local" in payload


def test_weekly_handover_endpoint_range_mode(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Accepts start_local / end_local datetimes."""

    def _fake_generate_weekly_handover(**kwargs: object) -> dict:
        assert kwargs.get("start_local") is not None
        return _fake_result()

    monkeypatch.setattr(
        "cast_llm.api.app.generate_weekly_handover",
        _fake_generate_weekly_handover,
    )

    client = TestClient(app)
    response = client.post(
        "/handover/weekly",
        json={
            "start_local": "2026-04-22T06:00:00",
            "end_local": "2026-04-29T06:00:00",
            "timezone": "Europe/London",
            "context_note": "Wednesday 6am",
        },
    )
    assert response.status_code == 200


def test_weekly_handover_rejects_mixed_mode() -> None:
    """Validation error if both week and range are provided."""
    client = TestClient(app)
    response = client.post(
        "/handover/weekly",
        json={
            "week_start_local": "2026-04-12",
            "start_local": "2026-04-12T00:00:00",
            "end_local": "2026-04-18T23:59:59",
            "timezone": "Europe/London",
        },
    )
    assert response.status_code == 422


def test_weekly_handover_bad_window_returns_400(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Service ValueError maps to HTTP 400."""

    def _raise(**_: object) -> dict:
        raise ValueError("end_local must be on or after start_local")

    monkeypatch.setattr(
        "cast_llm.api.app.generate_weekly_handover",
        _raise,
    )
    client = TestClient(app)
    response = client.post(
        "/handover/weekly",
        json={"week_start_local": "2026-04-12"},
    )
    assert response.status_code == 400
    assert "end_local" in response.json()["detail"]
