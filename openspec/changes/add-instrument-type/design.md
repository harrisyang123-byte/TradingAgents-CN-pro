## Context

当前持仓系统（`paper_positions`）只存储 market 字段（CN/HK/US），无标的分类。Tier 2 引擎中 `pos.get('instrument_type', 'stock')` 恒为 `'stock'`。新增 `instrument_type` 字段需端到端贯通 5 层，但引擎层已有兼容代码无需改动。

## Goals / Non-Goals

**Goals:**
- 前端添加/编辑持仓表单提供分类选择器（stock/etf/fund/bond/other）
- 输入 A 股代码时自动识别 ETF vs 股票，用户可覆盖
- 后端 API 接受并持久化 instrument_type
- PortfolioService 返回 instrument_type

**Non-Goals:**
- 不修改 Tier 2 引擎代码（已有 `pos.get('instrument_type', 'stock')` 兼容）
- 不迁移旧数据（旧文档无此字段时降级为 'stock'）
- 不添加新的分类类型（5 种足够当前使用，后续可扩展）

## Decisions

### Decision 1: 自动识别放在前端还是后端

**选前端**。理由：
- 代码识别是纯规则匹配，无 IO 依赖，适合前端即时反馈
- 后端 `_detect_market_and_code` 已有类似模式（识别市场），但 instrument_type 识别更简单
- 用户需要即时看到识别结果并有机会修改，后端识别会让交互变慢（需等 API 响应）

前端 `detectInstrumentType(code, market)` 函数规则：
- 仅对 A 股生效（market === 'CN'）
- 代码以 `159`/`510`/`511`/`512`/`513`/`515`/`516`/`517`/`518`/`588`/`560`/`561`/`562`/`563` 开头 → `etf`
- 其他 A 股代码 → `stock`
- 港股/美股 → `stock`（不做 ETF 识别，如 SPY/QQQ 等）

### Decision 2: instrument_type 的可选性

**在 API 层面设为 Optional，写入时缺省为 "stock"**。

- `AddPositionRequest.instrument_type: Optional[str]` — 不传时后端填 `"stock"`
- `UpdatePositionRequest.instrument_type: Optional[str]` — 不传时不更新（保留原值）
- 前端表单：分类选择器必选（自动识别提供默认值，用户永远不用面对空选择）

### Decision 3: 前端 UI 展示

| 类型 | 标签文字 | Element Plus Tag 类型 |
|------|---------|---------------------|
| stock | 股票 | `success` (green) |
| etf | ETF | `primary` (blue) |
| fund | 基金 | `warning` (orange) |
| bond | 债券 | `info` (gray) |
| other | 其他 | `default` |
| null (旧数据) | 未分类 | `danger` (red) |

### Decision 4: 端到端数据流

```
用户输入代码 → 前端 detectInstrumentType() → 展示默认分类 → 用户确认/修改
→ POST /api/portfolio/positions { ..., instrument_type: "etf" }
→ paper.py add_position() → MongoDB insert { instrument_type: "etf" }
→ PortfolioService.get_portfolio_summary() → { ..., instrument_type: "etf" }
→ AdvisorGraph.propagate_advice() → pos.get('instrument_type', 'stock') → "etf"
```

## Risks / Trade-offs

- **前端识别覆盖不全**：港股/美股 ETF（如 2800.HK, SPY）一律回退为 stock → 用户手动修改即可
- **旧数据字段缺失**：PortfolioService 降级返回 'stock'，前端显示"未分类"标签引导用户补充 → 可接受
- **零破坏性**：所有 API 新增字段均为 Optional，MongoDB 无需 schema migration

## Open Questions

- 无
