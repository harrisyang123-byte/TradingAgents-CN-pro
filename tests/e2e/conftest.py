"""E2E fixtures: authenticated API client + Playwright browser."""

import os
import time
import pytest
import httpx
import requests
from pathlib import Path

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:5173")
TEST_USER = os.environ.get("E2E_TEST_USER", "admin")
TEST_PASSWORD = os.environ.get("E2E_TEST_PASS", "admin123")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

TOKEN_CACHE: dict = {}


def _login() -> str:
    """Sync login via requests — avoids async fixture scope issues."""
    cache_key = (BASE_URL, TEST_USER, TEST_PASSWORD)
    if cache_key in TOKEN_CACHE:
        cached = TOKEN_CACHE[cache_key]
        if cached["expires"] > time.time():
            return cached["token"]

    url = f"{BASE_URL}/api/auth/login"
    resp = requests.post(
        url,
        json={"username": TEST_USER, "password": TEST_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        # Try register
        resp = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "username": TEST_USER,
                "email": f"{TEST_USER}@e2e.local",
                "password": TEST_PASSWORD,
            },
            timeout=10,
        )
        if resp.status_code not in (200, 201, 409):
            raise RuntimeError(f"E2E auth setup failed: register={resp.status_code}")
        resp = requests.post(
            url,
            json={"username": TEST_USER, "password": TEST_PASSWORD},
            timeout=10,
        )

    data = resp.json()
    if data.get("success"):
        token = data["data"]["access_token"]
    elif data.get("code") == 200:
        token = data["data"]["access_token"]
    else:
        raise RuntimeError(f"E2E login failed: {resp.status_code} {resp.text}")

    TOKEN_CACHE[cache_key] = {"token": token, "expires": time.time() + 300}
    return token


@pytest.fixture(scope="module")
def api_client() -> httpx.Client:
    """Authenticated synchronous httpx client."""
    token = _login()
    client = httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    yield client
    client.close()


@pytest.fixture(scope="module")
def api_client_async() -> httpx.AsyncClient:
    """Async version — only if needed for specific tests."""
    import asyncio

    token = _login()

    async def _make() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    client = loop.run_until_complete(_make())
    yield client
    loop.run_until_complete(client.aclose())
