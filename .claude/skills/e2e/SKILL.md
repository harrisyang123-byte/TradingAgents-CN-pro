---
name: e2e
description: Pull code from GitLab, analyze diff, write targeted E2E tests, and file issues for failures.
trigger: /e2e
---

# /e2e

从 GitLab 拉代码 → 分析 diff → 查 graphify 影响面 → 跑针对性测试 → 失败提 issue。

## 触发

`/e2e`、`跑E2E`、`跑测试`

## Workflow

### Phase 1 — Pull

```bash
git pull gitlab <current-branch>
```

If merge conflicts, report and stop.

### Phase 2 — Diff

```bash
git diff --name-only gitlab/<current-branch>...HEAD
```

List all changed files. If no changes: "没有新变更，无需测试。"

### Phase 3 — Impact analysis

1. Query graphify MCP: `get_node` on key changed files, `god_nodes` to find affected hubs.
2. Map changed files → affected communities using `tests/e2e/utils.py:files_to_communities()`.
3. Print a summary table: `| 文件 | 受影响社区 | 建议场景 |`

### Phase 4 — Write/update scenarios

- Read `tests/e2e/scenarios/` to see what tests already exist.
- For each affected community that has **no scenario file**, create one following the pattern of existing files.
- For communities that already have scenarios, add test functions for newly affected paths.
- Each test function: one endpoint or one UI path, clear assertion, docstring.

### Phase 5 — Run

```bash
cd tests && E2E_BASE_URL=http://localhost:8000 E2E_TEST_USER=admin E2E_TEST_PASS=admin123 .venv/bin/python -m pytest e2e/scenarios/ -v --tb=short
```

Frontend tests require `E2E_FRONTEND=1` and a running `npm run dev` at port 5173.

### Phase 6 — Report & Issue

For each failure:
1. Print: `❌ <test_name> — <reason>`
2. If `--issue` flag: create GitLab issue via `tests/e2e/utils.py:create_gitlab_issue()`

Summary format:
```
✅ X passed  ❌ Y failed  ⚠ Z errors
```

## Key files

- `tests/e2e/conftest.py` — fixtures (api_client, browser)
- `tests/e2e/utils.py` — diff analysis, community mapping, GitLab issue creation
- `tests/e2e/runner.py` — CLI runner
- `tests/e2e/scenarios/test_api_*.py` — API tests
- `tests/e2e/scenarios/test_frontend_*.py` — Playwright UI tests

## Constraints

- Never skip the diff analysis step. Only test what changed.
- Test files go in `tests/e2e/scenarios/`.
- One scenario module per domain area (portfolio, advice, auth, etc.)
- GitLab issue body must include: changed files, affected communities, test output.
- Don't test unchanged code paths — respect the diff.
