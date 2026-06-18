"""E2E: Frontend Portfolio Overview page tests (Playwright).

Set E2E_FRONTEND=1 to enable these tests.
"""

import os
import time
import pytest
import requests

FRONTEND_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:5173")
BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
TEST_USER = os.environ.get("E2E_TEST_USER", "admin")
TEST_PASSWORD = os.environ.get("E2E_TEST_PASS", "admin123")

pytestmark = pytest.mark.skipif(
    not os.environ.get("E2E_FRONTEND"), reason="E2E_FRONTEND not set"
)


def _login() -> str:
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": TEST_USER, "password": TEST_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed: {resp.status_code}")
    return resp.json()["data"]["access_token"]


@pytest.fixture(scope="module")
def page():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


def test_overview_page_loads(page):
    """Portfolio Overview page loads without error."""
    token = _login()
    page.goto(f"{FRONTEND_URL}/portfolio/overview")
    page.evaluate(f"""localStorage.setItem('token', '{token}')""")
    page.reload()
    time.sleep(2)
    body_text = page.inner_text("body")
    assert "行业" in body_text or "加载" in body_text or "暂无" in body_text


def test_matrix_table_renders(page):
    """Industry matrix card is visible."""
    token = _login()
    page.goto(f"{FRONTEND_URL}/portfolio/overview")
    page.evaluate(f"""localStorage.setItem('token', '{token}')""")
    page.reload()
    time.sleep(3)
    body = page.inner_text("body")
    assert "行业配置矩阵" in body, "Matrix card should be visible"


def test_debate_card(page):
    """Page loads and renders debate section if data exists."""
    token = _login()
    page.goto(f"{FRONTEND_URL}/portfolio/overview")
    page.evaluate(f"""localStorage.setItem('token', '{token}')""")
    page.reload()
    time.sleep(3)
    body = page.inner_text("body")
    assert len(body) > 10, "Page should have content"
