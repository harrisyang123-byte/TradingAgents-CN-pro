# 变更提案：个人专属理财助手

**变更 ID**: portfolio-advisor
**优先级**: P1
**状态**: 规划中

## 背景

TG-CN 目前是"一次性分析工具"：输入 ticker，跑分析，看报告，结束。系统不知道用户持有什么、投了多少钱、盈亏如何。分析建议无法考虑用户仓位状况。

## 目标

变成用户的专属理财助手——知道用户的真实持仓、资金、盈亏，给出个性化投资建议。

## Capabilities

### portfolio-crud
改造 PaperTrading 模块为真实持仓管理。单账户单钱包（人民币计价），多市场持仓（A股/港股/美股），港股/美股市值按中国银行汇率折算。

录入方式：
- **CLI**：Claude Code 对话录入，AI 解析后调 REST API
- **Web**：前端"添加持仓"弹窗，用户手动填写代码/数量/价格/日期

数据模型：PortfolioAccount（总投入 + 可用现金）、Position（持仓）、Transaction（交易记录）。

总盈亏 = (持仓市值 + 可用现金) - 总投入。

### portfolio-context-injection
在分析引擎中注入用户持仓上下文。propagate() 接受 portfolio_context 字符串参数，Portfolio Manager prompt 中展示用户当前持仓、仓位占比、盈亏情况，使分析建议个性化。

### portfolio-frontend
前端"模拟交易"改造为"我的持仓"。新增：账户总览统计卡片、仓位分布饼图、盈亏贡献图表、手动添加持仓弹窗。删除：虚拟资金逻辑、风险提示横幅。

## 不做什么

- 不接入真实券商 API
- 不做自动下单
- 不做基金管理（后续 Phase 3）
- 组合诊断 + 主动发现新标的（后续 Phase 2）
- 自由发现模式（后续 Phase 2）

## PRD

详见 `planning/v1/portfolio_prd.md`（O.A.I.S 四层完整 PRD）。

## 原型

详见 `planning/v1/portfolio_prototype.html`（可交互 HTML 原型）。
