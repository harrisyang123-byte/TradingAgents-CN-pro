# 持仓管理 (Portfolio CRUD)

**变更**: portfolio-advisor
**日期**: 2026-05-18

## 概述

将 PaperTrading 模块改造为真实持仓管理系统。单账户单钱包（人民币计价），多市场持仓（A股/港股/美股），港股/美股市值按中国银行汇率折算人民币。

## 数据模型

### 账户 (`paper_accounts`)

| 字段 | 类型 | 说明 |
|------|------|------|
| available_cash | float | 可用现金（人民币） |
| total_invested | float | 总投入资金 |

旧格式兼容：检测到 `cash` 字段为 dict 时，取 `cash.CNY` 值迁移到 `available_cash`。

### 持仓 (`paper_positions`)

| 字段 | 类型 | 说明 |
|------|------|------|
| code | str | 标准化代码（A股6位/港股5位/美股字母） |
| market | str | CN / HK / US |
| currency | str | CNY / HKD / USD |
| quantity | int | 持仓数量 |
| avg_cost | float | 加权平均成本 |

总盈亏公式：`(持仓市值_CNY + 可用现金) - 总投入`

## 实现要点

### 路由前缀

`/paper` → `/portfolio`，旧路由 `/paper` 重定向到 `/portfolio`。

### 汇率服务

`PortfolioService._get_exchange_rate(currency)` — AKShare `currency_boc_safe`（中国银行外汇牌价），缓存到 MongoDB `exchange_rates` 集合，TTL 24h。Fallback：HKD 0.92, USD 7.25。

### 持仓上下文注入

数据流：`simple_analysis_service._execute_analysis_sync()` → `PortfolioService.get_portfolio_context(user_id)` → `propagate(portfolio_context=ctx)` → `state["portfolio_context"]` → Portfolio Manager prompt。

引擎层不做数据库查询，保持纯净。上下文构造在服务层完成。

### 前端

"我的持仓"页面：4 统计卡片（总资产/总投入/可用现金/总盈亏）+ ECharts 仓位饼图 + 持仓表格（带仓位进度条 + 盈亏着色）。

## 关键决策

1. **改造 vs 新建** — 改造 `paper.py`，PaperTrading 已有 90% 基础设施
2. **单账户 vs 多币种** — 单账户单钱包人民币，用户实际只有一笔钱
3. **汇率来源** — 中行外汇牌价日频缓存，非实时汇率（过度设计）
4. **注入点** — 在 `simple_analysis_service` 构造上下文，不在引擎层查数据库
5. **价格填写** — 用户手动填写成交价（非自动市价），因为是录入真实持仓
