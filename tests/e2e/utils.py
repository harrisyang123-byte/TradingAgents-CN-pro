"""GitLab issue creation + diff impact analysis for E2E workflow."""

import json
import subprocess
import os
import urllib.request
import urllib.error
from pathlib import Path

GITLAB_URL = "http://gitlab.xiaopeng.local:18080"
GITLAB_PROJECT = "myself_yangyy5%2Fai-coding-engine"
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", "")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def create_gitlab_issue(title: str, description: str, labels: str = "e2e-failure") -> dict | None:
    """Create an issue on GitLab. Returns the issue dict or None on failure."""
    if not GITLAB_TOKEN:
        print("[e2e] GITLAB_TOKEN not set — skipping issue creation")
        return None

    url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT}/issues"
    body = {"title": title, "description": description, "labels": labels}

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "PRIVATE-TOKEN": GITLAB_TOKEN,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            print(f"[e2e] GitLab issue created: {result.get('web_url', result.get('iid', '?'))}")
            return result
    except Exception as e:
        print(f"[e2e] Failed to create GitLab issue: {e}")
        return None


def get_changed_files(base: str = "main") -> list[str]:
    """Return list of files changed on current branch vs base."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", base + "...HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
        ).strip()
        return [f for f in out.splitlines() if f] if out else []
    except subprocess.CalledProcessError:
        return []


def get_changed_files_since_pull(remote_branch: str = "gitlab/main") -> list[str]:
    """Return files changed after `git pull gitlab ...`."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", remote_branch + "...HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
        ).strip()
        return [f for f in out.splitlines() if f] if out else []
    except subprocess.CalledProcessError:
        return []


# ── Community → Test scenario mapping ──
# Maps graphify community names to scenario module + test functions.
# Extended as we learn more communities.

COMMUNITY_TO_SCENARIO: dict[str, list[tuple[str, str]]] = {
    "Portfolio Service": [
        ("test_api_portfolio", "test_overview_matrix"),
        ("test_api_portfolio", "test_overview_total_assets"),
        ("test_api_portfolio", "test_positions_list"),
    ],
    "Proposal & Portfolio Rendering": [
        ("test_frontend_overview", "test_matrix_table_renders"),
        ("test_frontend_overview", "test_drawer_opens"),
        ("test_frontend_overview", "test_debate_card"),
    ],
    "Advisor Graph (L1)": [
        ("test_api_advice", "test_generate_advice"),
        ("test_api_advice", "test_latest_advice_fields"),
    ],
    "Advisor Debate States": [
        ("test_api_advice", "test_debate_history_fields"),
        ("test_frontend_overview", "test_debate_tabs"),
    ],
    "Database Data Access": [
        ("test_api_health", "test_mongodb_reachable"),
    ],
    "Authentication & Config": [
        ("test_api_auth", "test_login"),
    ],
    "ACE Workflow Agents": [],  # tooling, no direct E2E
    "Docker & System Init": [],  # infra, not runtime
}


def files_to_communities(changed_files: list[str]) -> set[str]:
    """Map changed files to likely graphify communities (rule-based fallback)."""
    communities: set[str] = set()

    # Python backend
    for f in changed_files:
        if "paper.py" in f or "portfolio" in f.lower():
            communities.add("Portfolio Service")
            communities.add("Proposal & Portfolio Rendering")
        if "advisor" in f.lower() or "graph" in f.lower():
            communities.add("Advisor Graph (L1)")
            communities.add("Advisor Debate States")
        if "model" in f.lower() or "schema" in f.lower():
            communities.add("Database Data Access")
        if "auth" in f.lower() or "login" in f.lower():
            communities.add("Authentication & Config")
        if "db" in f.lower() or "mongo" in f.lower():
            communities.add("Database Data Access")

    # Vue frontend
    for f in changed_files:
        if f.endswith(".vue"):
            communities.add("Proposal & Portfolio Rendering")
            communities.add("UI & User Management")

    return communities or {"Portfolio Service"}  # default fallback


def impact_report(changed_files: list[str]) -> dict:
    """Build an impact report: which files, communities, and scenarios to test."""
    communities = files_to_communities(changed_files)
    scenarios: list[tuple[str, str]] = []
    for comm in communities:
        scenarios.extend(COMMUNITY_TO_SCENARIO.get(comm, []))

    # Deduplicate (module, function) pairs
    seen = set()
    unique: list[tuple[str, str]] = []
    for m, fn in scenarios:
        key = (m, fn)
        if key not in seen:
            seen.add(key)
            unique.append(key)

    return {
        "changed_files": changed_files,
        "affected_communities": sorted(communities),
        "scenarios": unique,
    }
