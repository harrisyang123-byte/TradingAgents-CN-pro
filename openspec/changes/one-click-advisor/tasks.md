# 一键组合顾问 — 任务

- [x] `cli/claude_advisor.py`：`--user-id` 改为可选，新增 `_auto_detect_user()`
- [x] `CLAUDE.md`：快捷指令表更新，`.venv/bin/python` 替代 `python3`
- [x] `README.md`：快速启动重新编排
- [x] `app/core/database.py`：添加 `_db_initialized` 守卫，消除重复初始化
- [x] `cli/advisor/data_collector.py`：`_db_ready` 守卫 + 删除死代码 + 除零保护
- [x] `cli/claude_advisor.py`：修复 Event loop is closed — 所有异步逻辑合并到单一 `amain()`，一个 `asyncio.run()` 调度
- [x] E2E 全链路验证（第2轮）：事件循环修复后重跑，923s 产出 72 条处方（6 buy / 2 sell / 64 hold），无 RuntimeError
