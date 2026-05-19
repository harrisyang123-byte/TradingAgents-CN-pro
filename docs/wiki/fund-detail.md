# 基金详情 (FundDetail)

**变更**: fund-detail-page
**日期**: 2026-05-19

## 概述

为持仓列表中的基金代码提供独立的详情页面，展示基金基础信息、前十大重仓股、行业分布三项核心穿透数据，打通 Tier 2 数据底座。

## 实现要点

- **后端 API**: 三个独立端点 `/api/fund/basic-info`、`/api/fund/top-holdings`、`/api/fund/sector-distribution`，独立加载不互相阻塞
- **数据源**: AKShare（`fund_individual_basic_info_xq`、`fund_portfolio_hold_em`、`fund_portfolio_industry_allocate_em`）
- **缓存策略**: 30 天双级缓存（内存 → MongoDB `fund_data_cache` 集合），基金持仓数据季度更新
- **异步调用**: AKShare 同步接口通过 `asyncio.to_thread` 包装，避免阻塞事件循环
- **前端路由**: `/portfolio/fund/:code` 嵌套在持仓模块下
- **前端状态**: 各数据区域独立 loading/empty/error 三态 + 整体页面 loading/empty/error 覆盖

## 关键决策

- 多端点 API 而非单一聚合：最慢的数据不拖慢整个页面，部分失败不影响其他区域
- 30 天缓存：基金持仓季度更新，缓存长于月报周期
- CSS `conic-gradient` 饼图替代第三方图表库：零依赖，原型一致
- 基金代码点击导航区分 `instrument_type`：fund → FundDetail，其他 → StockDetail

## 注意事项

- AKShare 接口可能超时，前端设 10s 超时，各区域独立重试
- 部分基金不披露持仓，重仓股和行业分布返回空列表，前端展示空态
- 持仓数据按季度更新，非实时，页面标注数据来源时间
