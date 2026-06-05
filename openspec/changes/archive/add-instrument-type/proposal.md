## Why

当前持仓系统只能区分市场（CN/HK/US），无法区分标的类型。用户添加基金/ETF/债券时，Tier 2 组合顾问引擎一律按"股票"分析，给出不准确的操作建议。需要在全链路贯通 `instrument_type` 字段。

## What Changes

- 前端添加/编辑持仓表单新增**标的分类下拉选择器**（股票/ETF/基金/债券/其他）
- 输入股票代码时**自动识别分类**（A 股 ETF 代码规则 + 手动回退），用户可覆盖
- 后端 API 接受并持久化 `instrument_type` 字段到 MongoDB
- `PortfolioService.get_portfolio_summary()` 返回 `instrument_type`
- Tier 2 引擎 `AdvisorGraph` 读取真实分类，不再退化到 `'stock'`
- 旧持仓兼容：无 `instrument_type` 时前端显示"未分类"，引擎降级为 `stock`

## Capabilities

### New Capabilities
- `instrument-type`: 持仓标的分类字段，支持 stock/etf/fund/bond/other 五种类型，端到端贯通前端表单 → API → MongoDB → 数据服务 → AI 引擎

### Modified Capabilities
<!-- No existing spec-level requirements to modify -->

## Impact

- **前端**: `src/api/paper.ts`（类型定义）, `src/views/PaperTrading/index.vue`（表格列 + 表单 + 自动识别）
- **后端**: `app/routers/paper.py`（API 模型 + 路由）, `app/services/portfolio_service.py`（数据聚合）
- **引擎**: `tradingagents/agents/advisors/*.py`（无需改动——已读 `pos.get('instrument_type', 'stock')`）
- **数据库**: `paper_positions` 文档新增可选字段，旧文档无需迁移
- **无破坏性变更**
