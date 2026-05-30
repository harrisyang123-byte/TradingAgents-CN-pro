# Spec: CIO Decision Card Output

## ADDED Requirements

### Requirement: 6-Field Decision Card JSON
The CIO SHALL output prescriptions with 7 additional fields (l1_context, l2_context, suggested_price, max_loss_pct, five_year_view, bias_check, priority) beyond the existing 6 fields, and MUST preserve backward compatibility with the existing `_parse_prescription()` parser.

#### Scenario: 完整决策卡片输出
- **GIVEN** CIO 执行初稿或终裁，`price_context` 可用且 L1/L2 裁判报告覆盖该标的
- **WHEN** CIO 生成处方
- **THEN** 每条处方 JSON 包含 `l1_context`, `l2_context`, `suggested_price`, `max_loss_pct`, `five_year_view`, `bias_check`, `priority` 共 7 个新字段

#### Scenario: PE 分位不可用时的 suggested_price
- **GIVEN** `price_context[code].pe_percentile_5y` 为 null
- **WHEN** CIO 生成该标的处方
- **THEN** `suggested_price` 仅引用 MA20 和当前 PE 绝对值做定性判断，不引用分位数据

#### Scenario: L1/L2 裁判未覆盖标的
- **GIVEN** 某候选标的不在 L1/L2 裁判报告中
- **WHEN** CIO 生成该标的处方
- **THEN** `l1_context` 标注"未覆盖"，`l2_context` 标注"经由 L2 Scout 筛选"

### Requirement: 优先级判定
The CIO MUST assign a priority level (urgent/important/optional) to each prescription based on action urgency and risk severity, with risk-related actions defaulting to urgent.

#### Scenario: 减仓信号为 urgent
- **GIVEN** CIO 判断某标的需减仓/清仓（风险总监发现严重风险暴露）
- **WHEN** 生成处方
- **THEN** `priority: "urgent"`

#### Scenario: 新买入好机会为 important
- **GIVEN** CIO 判断某标的具备安全边际，是加仓时机
- **WHEN** 生成处方
- **THEN** `priority: "important"`

#### Scenario: 观察列表为 optional
- **GIVEN** CIO 判断某标的可关注但无需立即行动
- **WHEN** 生成处方
- **THEN** `priority: "optional"`

### Requirement: Existing Fields Preservation
The `_parse_prescription()` function MUST continue to parse all existing fields (code, name, instrument_type, action, current_weight, target_weight, reasoning, risk_note) and SHALL accept new fields as optional additions without breaking when they are absent.

#### Scenario: 向后兼容
- **GIVEN** 处方 JSON 包含 7 个新字段
- **WHEN** `_parse_prescription()` 解析
- **THEN** 现有 8 字段正常解析，新字段作为可选附加，旧格式处方（无新字段）同样可解析

### Requirement: Edge Case — 空 price_context
The CIO MUST produce valid prescriptions even when `price_context` is empty (all data sources unavailable), with `suggested_price` degraded to pure qualitative judgment, and SHALL not block prescription generation due to missing price data.

#### Scenario: enrich_price_data 失败不阻塞 CIO
- **GIVEN** `enrich_price_data_node` 因全部数据源不可用而返回空的 `price_context`
- **WHEN** CIO 执行
- **THEN** CIO 正常输出处方，`suggested_price` 降级为纯定性判断，不影响其他 6 个新字段
