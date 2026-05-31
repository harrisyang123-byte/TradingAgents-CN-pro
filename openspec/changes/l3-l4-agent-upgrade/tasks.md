# L3/L4 Agent 升级 — 实现任务

## Slice 1: 工具函数（4 个新文件）

1. [x] 新建 `cio_tools.py` — CIO 6 个工具
2. [x] 新建 `analyst_tools.py` — Analyst 2 个工具
3. [x] 新建 `strategist_tools.py` — Strategist 3 个工具
4. [x] 新建 `risk_tools.py` — Risk Director 2 个工具

## Slice 2: Agent 重写（4 个文件）

5. [x] 重写 `analyst.py` → 工具型 Agent
6. [x] 重写 `strategist.py` → 工具型 Agent
7. [x] 重写 `cio.py` → 工具型 Agent
8. [x] 重写 `risk_director.py` → 工具型 Agent

## Slice 3: 图 + 状态 + 导出

9. [x] 修改 `advisor_states.py` — 新增计数器字段
10. [x] 修改 `__init__.py` — 导出新符号
11. [x] 修改 `advisor_graph.py` — L3/L4 加 ToolNode + 条件边

## Slice 4: CLI 入口

12. [x] 新建 `cli/run_advisor.py`

## Slice 5: 验证

13. [x] 语法检查：`python -m py_compile` 逐个文件
14. [x] CLI 完整执行：`python cli/run_advisor.py run --user-id 6a094caea814b57d3357fa0b`
