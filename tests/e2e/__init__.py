"""
E2E test infrastructure for TradingAgents-CN.

Workflow:
  1. git pull gitlab <branch>
  2. Read diff → which files changed?
  3. Query graphify MCP → which communities affected?
  4. Run targeted scenarios based on blast radius
  5. File GitLab issues for failures

Fixtures:
  - api_client:   httpx.AsyncClient with Bearer auth (against http://localhost:8000)
  - browser_page: Playwright Chromium page (against http://localhost:5173)
"""

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
