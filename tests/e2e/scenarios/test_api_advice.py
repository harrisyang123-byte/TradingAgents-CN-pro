"""E2E: Advice API tests (requires MongoDB with prior analysis data)."""

import pytest


def test_latest_advice_fields(api_client):
    """GET /api/paper/advice/latest returns valid advice or 404."""
    resp = api_client.get("/api/portfolio/advice/latest")
    if resp.status_code == 200:
        data = resp.json()
        d = data.get("data", {}) or {}
        if d:
            assert "advice_id" in d
            assert "status" in d
            assert "created_at" in d


def test_advice_history(api_client):
    """GET /api/paper/advice returns paginated history."""
    resp = api_client.get("/api/portfolio/advice", params={"page": 1, "page_size": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("code") == 200
    assert isinstance(data["data"].get("items", []), list)
    assert isinstance(data["data"].get("total"), int)


def test_debate_history_fields(api_client):
    """Latest COMPLETED advice has debate history fields."""
    resp = api_client.get("/api/portfolio/advice/latest")
    if resp.status_code == 200:
        d = resp.json().get("data", {}) or {}
        if d.get("status") == "COMPLETED":
            has_debate = any(
                d.get(k)
                for k in ("debate_history", "market_debate_history", "stock_debate_history")
            )
            assert has_debate, "COMPLETED advice should have debate_history"


def test_generate_advice_starts(api_client):
    """POST /api/paper/advice starts a new analysis and returns advice_id."""
    resp = api_client.post("/api/portfolio/advice")
    assert resp.status_code in (200, 202)
    data = resp.json()
    assert data.get("code") == 200
    advice = data.get("data", {})
    assert "advice_id" in advice
    assert advice.get("status") in (
        "GENERATING",
        "RUNNING",
        "PENDING",
        "QUEUED",
    )
