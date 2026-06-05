# 一键组合顾问 — 任务

- [x] `cli/claude_advisor.py`：`--user-id` 改为可选，新增 `_auto_detect_user()`
- [x] `CLAUDE.md`：快捷指令表更新，`.venv/bin/python` 替代 `python3`
- [x] `README.md`：快速启动重新编排
- [x] `app/core/database.py`：添加 `_db_initialized` 守卫，消除重复初始化
- [x] `cli/advisor/data_collector.py`：`_db_ready` 守卫 + 删除死代码 + 除零保护
- [x] E2E 全链路验证：MongoDB 8.0 + Redis 8.8 + DeepSeek API，9 Agent 全部成功，146s 产出 36 条处方
