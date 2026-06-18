#!/usr/bin/env python3
"""
E2E Test Runner — diff-driven.

Workflow:
  1. git pull gitlab <branch>
  2. git diff → changed files
  3. Map files → communities → scenarios
  4. Run targeted pytest scenarios
  5. File GitLab issues for failures

Usage:
  .venv/bin/python tests/e2e/runner.py [--branch feature/xxx] [--base main]
  .venv/bin/python tests/e2e/runner.py --since-pull gitlab/main
"""

import argparse
import json
import subprocess
import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)

# Add project root so we can import e2e utils
sys.path.insert(0, str(PROJECT_ROOT))
from tests.e2e.utils import (
    get_changed_files,
    files_to_communities,
    impact_report,
    create_gitlab_issue,
    COMMUNITY_TO_SCENARIO,
)


def git_pull_gitlab(branch: str) -> bool:
    """Pull from gitlab remote. Returns True on success."""
    print(f"[e2e] Pulling gitlab/{branch} ...")
    try:
        subprocess.run(
            ["git", "fetch", "gitlab", branch],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "merge", f"gitlab/{branch}"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("[e2e] Pull OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[e2e] Pull failed: {e.stderr}")
        return False


def run_targeted_tests(scenarios: list[tuple[str, str]], backend: str) -> dict:
    """Run only the specified (module, function) pairs via pytest -k."""
    if not scenarios:
        return {"passed": [], "failed": [], "errors": [], "output": "No scenarios selected"}

    # Build pytest -k expression
    func_names = [fn for _, fn in scenarios]
    k_expr = " or ".join(func_names)

    cmd = [
        sys.executable,
        "-m", "pytest",
        str(PROJECT_ROOT / "tests" / "e2e" / "scenarios"),
        "-v",
        "--tb=short",
        "-k", k_expr,
        "--no-header",
    ]

    print(f"[e2e] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Parse outcome
    output = result.stdout + "\n" + result.stderr
    passed: list[str] = []
    failed: list[str] = []
    errors: list[str] = []

    for line in result.stdout.splitlines():
        line = line.strip()
        if "PASSED" in line or "passed" in line and "::" in line:
            passed.append(line)
        elif "FAILED" in line and "::" in line:
            failed.append(line)
        elif "ERROR" in line and "::" in line:
            errors.append(line)

    # Count from pytest summary
    summary = {"passed": len(passed), "failed": len(failed), "errors": len(errors)}

    # Try to get exact counts from summary line
    for line in result.stdout.splitlines():
        if "passed" in line and "failed" in line:
            parts = line.strip().split(",")
            for p in parts:
                p = p.strip()
                if p.endswith("passed"):
                    try:
                        summary["passed"] = int(p.split()[0])
                    except ValueError:
                        pass
                elif p.endswith("failed"):
                    try:
                        summary["failed"] = int(p.split()[0])
                    except ValueError:
                        pass
                elif p.endswith("errors"):
                    try:
                        summary["errors"] = int(p.split()[0])
                    except ValueError:
                        pass

    return {
        **summary,
        "output": output[-3000:],  # truncated for issue body
        "passed_list": passed[-30:],
        "failed_list": failed,
        "error_list": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="E2E diff-driven test runner")
    parser.add_argument("--branch", help="GitLab branch to pull")
    parser.add_argument("--base", default="main", help="Base branch for diff (default: main)")
    parser.add_argument(
        "--since-pull",
        help="Remote ref to diff against after pulling (e.g., gitlab/main)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show impact report only, don't test")
    parser.add_argument("--backend", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--issue", action="store_true", help="Create GitLab issues for failures")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all E2E scenarios regardless of diff",
    )
    args = parser.parse_args()

    start = time.time()

    # 1. Pull if requested
    if args.branch:
        if not git_pull_gitlab(args.branch):
            sys.exit(1)

    # 2. Get changed files
    if args.all:
        changed_files = ["app/routers/paper.py", "frontend/src/views/Portfolio/Overview.vue"]
        print("[e2e] --all mode: testing full portfolio coverage")
    elif args.since_pull:
        # Compare against the pulled remote branch
        outcome = subprocess.run(
            ["git", "diff", "--name-only", args.since_pull + "...HEAD"],
            capture_output=True,
            text=True,
        )
        changed_files = [f for f in outcome.stdout.splitlines() if f]
    else:
        changed_files = get_changed_files(args.base)

    if not changed_files:
        print("[e2e] No changed files — nothing to test")
        return

    print(f"[e2e] Changed files ({len(changed_files)}):")
    for f in changed_files:
        print(f"  {f}")

    # 3. Build impact report
    report = impact_report(changed_files)
    print(f"\n[e2e] Affected communities ({len(report['affected_communities'])}):")
    for c in report["affected_communities"]:
        print(f"  {c}")
    print(f"\n[e2e] Scenarios to run ({len(report['scenarios'])}):")
    for mod, fn in report["scenarios"]:
        print(f"  {mod}::{fn}")

    if args.dry_run:
        return

    # 4. Run tests
    results = run_targeted_tests(report["scenarios"], args.backend)

    elapsed = time.time() - start
    total = results["passed"] + results["failed"] + results["errors"]

    print(f"\n[e2e] Results: {results['passed']} passed, {results['failed']} failed, "
          f"{results['errors']} errors in {elapsed:.1f}s")

    # 5. Create GitLab issues for failures
    if args.issue and (results["failed"] > 0 or results["errors"] > 0):
        title = f"E2E: {results['failed']} failed, {results['errors']} errors"
        desc = (
            f"## Changed files\n"
            + "\n".join(f"- `{f}`" for f in changed_files)
            + f"\n\n## Affected communities\n"
            + "\n".join(f"- {c}" for c in report["affected_communities"])
            + f"\n\n## Failed scenarios\n"
            + "\n".join(f"- `{s[0]}::{s[1]}`" for s in report["scenarios"])
            + f"\n\n## Test output\n```\n{results['output'][:2000]}\n```\n"
            + f"\n\nBranch: `{args.branch or 'current'}`  \n"
            + f"Elapsed: {elapsed:.1f}s  \n"
        )
        issue = create_gitlab_issue(title, desc)
        if issue:
            print(f"[e2e] Issue: {issue.get('web_url', '')}")


if __name__ == "__main__":
    main()
