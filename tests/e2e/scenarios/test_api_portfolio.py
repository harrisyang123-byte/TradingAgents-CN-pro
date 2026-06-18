"""E2E: Portfolio Overview API tests."""

import pytest


def test_overview_matrix(api_client):
    """GET /api/paper/overview returns matrix with industries."""
    resp = api_client.get("/api/portfolio/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("code") == 200
    matrix = data["data"].get("matrix", [])
    assert isinstance(matrix, list)
    if matrix:
        row = matrix[0]
        assert "industry" in row
        assert "go_nogo" in row


def test_overview_total_assets(api_client):
    """GET /api/paper/overview includes total_assets field."""
    resp = api_client.get("/api/portfolio/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("code") == 200
    assert "total_assets" in data["data"]


def test_overview_covered_count(api_client):
    """GET /api/paper/overview has covered_count / stale_count / never_count."""
    resp = api_client.get("/api/portfolio/overview")
    assert resp.status_code == 200
    data = resp.json()
    d = data["data"]
    for key in ("covered_count", "stale_count", "never_count", "total_industries"):
        assert isinstance(d.get(key), int), f"{key} should be int"


def test_positions_list(api_client):
    """GET /api/paper/positions returns items list."""
    resp = api_client.get("/api/portfolio/positions")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("code") == 200
    assert isinstance(data["data"].get("items", []), list)


def test_summary(api_client):
    """GET /api/paper/summary returns portfolio summary."""
    resp = api_client.get("/api/portfolio/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("code") == 200
    summary = data["data"]
    assert "total_assets" in summary
