# Tasks: Portfolio Advisor Four-Level

## 1. State & Tools (基础设施)

- [x] 1.1 更新 `advisor_states.py`: 新增 messages + 9 字段 + 3 debate TypedDicts，移除 non_held_reports
- [x] 1.2 创建 `market_tools.py`: 9 个 AKShare/yfinance 工具函数（3 L1 + 5 L2 + 1 fund）

## 2. L1 行业方向

- [x] 2.1 创建 `market_strategist.py`: tool-agent，生命周期五阶段模型
- [x] 2.2 创建 `contrarian.py`: tool-agent，逆向挑战
- [x] 2.3 创建 `macro_judge.py`: 裁判，Go/NoGo 裁定

## 3. L2 标的筛选

- [x] 3.1 重写 `scout.py`: tool-agent + 巴芒四层过滤器
- [x] 3.2 创建 `stock_contrarian.py`: tool-agent，标的挑战
- [x] 3.3 创建 `stock_judge.py`: 裁判，推荐/观察/淘汰裁定

## 4. L4 最终处方

- [x] 4.1 创建 `risk_director.py`: 风险总监审查
- [x] 4.2 增强 `cio.py`: 芒格心智模型 + dual-mode（初稿/终裁）

## 5. L3 适配

- [x] 5.1 更新 `analyst.py`: prompt 注入 L1/L2 数据
- [x] 5.2 更新 `strategist.py`: prompt 注入 L1/L2 数据
- [x] 5.3 更新 `__init__.py`: 新导出

## 6. Graph 拓扑

- [x] 6.1 重写 `advisor_graph.py`: 四层拓扑 + ToolNode + Msg Clear + 条件路由 + 辩论循环

## 7. Service & Frontend

- [x] 7.1 更新 `portfolio_advisor_service.py`: 移除 non_held_reports，保存新字段
- [x] 7.2 更新 `paper.ts`: 新类型定义
- [x] 7.3 更新 `PaperTrading/index.vue`: 5 个新可折叠 section
- [x] 7.4 更新 `test_advisor_e2e.py`: 移除 non_held_reports 参数

## 8. Verification (Reviewer 阶段)

- [x] 8.1 Python 语法检查通过
- [x] 8.2 端到端：Graph 拓扑完整性验证通过（36 nodes + 32 edges + 8 branch routers）
- [x] 8.3 降级测试：工具层 fallback 逻辑验证通过（unsupported market / yfinance / AKShare 异常均不崩溃）
- [x] 8.4 回归测试：83/83 tests passed，0 failures
