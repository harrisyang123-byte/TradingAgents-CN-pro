# 持仓品种分类（instrument_type）

**变更**: add-instrument-type
**日期**: 2026-06-05

## 概述

`paper_positions` 集合新增 `instrument_type` 字段，支持 stock/etf/fund/bond/other 五种分类。前端录入时自动识别 A 股 ETF，用户可覆盖选择。

## 实现要点

- **API 层**：`AddPositionRequest` / `UpdatePositionRequest` 均为 `Optional[str]`，新增时缺省写入 `"stock"`，更新时不传则不覆盖原值
- **PortfolioService**：`get_portfolio_summary()` 返回 `instrument_type`，旧文档无此字段时降级为 `"stock"`
- **前端自动识别**：`detectInstrumentType(code, market)` 纯前端规则匹配，仅对 A 股生效；以 `159/510/511/512/513/515-518/588/560-563` 开头 → `etf`，其他 → `stock`

## 关键决策

**自动识别放前端**：代码识别是纯规则，无 IO 依赖，前端即时反馈、用户可覆盖；后端识别会增加交互延迟。

**instrument_type 对引擎透明**：Tier 2 引擎已有 `pos.get('instrument_type', 'stock')` 兼容写法，本次变更无需动引擎层。

## 注意事项

- 港股/美股 ETF（如 SPY/QQQ）不做自动 ETF 识别，统一标 `stock`；如需区分可在前端选择器手动选
- ETF 场内交易（`instrument_type == "etf"`）走 stock 行情分支，不走基金净值分支
