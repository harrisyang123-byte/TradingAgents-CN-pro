# Proposal: Portfolio Data Performance Fixes

## Why

持仓组合三页面（holdings/analysis/overview）上线后，E2E 验证发现四个关键数据问题阻塞用户使用：

1. **持仓明细加载超时（100s+）**：35 个持仓的`get_portfolio_summary`串行调用 AKShare，每次基金净值查询 3-5s，总耗时 ~100s，页面长期 Loading
2. **港股无名无价**：09992（泡泡玛特）、01810（小米）等港股无中文名称，最新价格缺失。根因：yfinance handler key 不匹配导致 yfinance 被过滤；无 HK 股名称查询回退
3. **行业覆盖矩阵全部"未分类"**：`paper_positions` 无 industry/sector 字段，覆盖矩阵中 35 个标的全部归入"未分类"
4. **持仓明细页 UI 不可用**：盈亏列表 35 行拉过长、无排序、饼图 35+ 切片不可读

这些不是功能缺失而是基础数据管道问题，阻塞用户验证已上线的三层架构。

## Design Overview

### 1. 并行化数据管道（后端）

`portfolio_service.py` 的 `get_portfolio_summary` 从串行改为并行：
- 新增 `_fetch_position_detail()` 方法，用 `asyncio.gather` 并发执行价格/汇率/名称查询
- AKShare 阻塞调用包装为 `asyncio.to_thread` + `asyncio.wait_for` 超时
- HK 股名称回退到 yfinance（format: strip leading zeros → pad to 4 → `.HK`）
- 超时设置：价格 8s、汇率 5s、名称 12s

### 2. HK 股数据修复（后端）

`foreign_stock_service.py`：
- yfinance handler 添加 `'yfinance'` 别名，与默认 priority name 匹配

### 3. 行业分类（后端）

`paper.py` overview endpoint：
- 批量查询 `stock_basic_info` 获取 stock/etf 的行业字段
- 基金从名称关键词推断行业（keyword → industry map，覆盖 AI/债券/医药/消费等 20+ 分类）
- 兜底归入"其他"

### 4. 前端 UI 修复

`PaperTrading/index.vue`：
- 盈亏贡献默认展示 top 10，附加"展开全部"按钮
- 持仓明细表头可点击排序（市值/仓位/盈亏/盈亏率）
- 饼图仅展示 top 5 + "其他"聚合项

`Overview.vue`：
- 持仓标显示中文名称（标签）+ 代号（小字）
- 历史建议卡片点击修复：正确打开详情弹窗

## Scoping and Materialization

- **范围**：后端 3 文件（portfolio_service + foreign_stock_service + paper router）+ 前端 2 文件（Index + Overview）+ 1 类型文件（paper.ts）
- **不涉及**：分析流程、SSE 流式、advisor graph、数据模型变更
- **验证方式**：API curl 测试 + Playwright 页面渲染验证

<!-- Dialectical Analysis -->
**方案对比**：

- 方案 A（缓存预热 + 串行）：启动时全量缓存 AKShare 数据，后续串行读取。优点：改动最小。缺点：首次加载仍需等待；缓存过期后重新预热；增量更新困难。
- 方案 B（并行化 + 超时 + 回退）：asyncio.gather 并发 + 多数据源回退。优点：无需预热、即时可用、HK 股双源互备。缺点：改动稍大、超时阈值需调优。

选择方案 B，理由：
1. 35 个持仓时未触发并行前串行 100s，触发后降为 ~8s（max 12s 名称超时），用户可接受
2. HK 股双源回退（akshare + yfinance）覆盖 A/H 双市场，无需额外配置
3. 超时 + 异常静默兜底确保不阻塞页面渲染

**风险对冲**：
- yfinance 可能被限流：初版使用同步调用，后续可增加缓存 + 重试
- 基金名称关键词推断可能误判：兜底 "其他" 而非强制分类
