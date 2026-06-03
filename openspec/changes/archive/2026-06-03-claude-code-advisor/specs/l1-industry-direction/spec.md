## MODIFIED Requirements

### Requirement: L1 行业哨兵部输出升级
L1 输出格式从 Go/NoGo 标签升级为超配/标配/低配/零配 + 量化指标。产出 SHALL 包含 ≥5 个可配置方向，每个方向 ≥200 字理由，含数据来源。策略师 SHALL 先调用 `get_industry_rankings`、`get_sector_fund_flows`、`get_macro_indicators` 获取数据后判定，不得只凭 LLM 常识。

#### Scenario: 多方向覆盖
- **WHEN** L1 辩论执行完成
- **THEN** 裁判输出包含所有用户持仓相关行业的超配/标配/低配/零配方向
- **AND** 至少 5 个方向被标记为超配或低配（含量化支撑）

#### Scenario: 数据驱动判定
- **WHEN** 策略师判定任一行业方向
- **THEN** 输出 SHALL 包含以下至少 2 项：PE 中位数、ROE 中位数、营收增速、资金流向数据
- **AND** 标注每项数据的具体来源（工具名 + 数值）

#### Scenario: 情绪修正
- **WHEN** 某行业基本面 Go + 行业资金流向为净流出
- **THEN** 策略师 SHALL 标注 "基本面 Go + 市场在卖出 = 可能有错杀风险，保持超配但降置信度半级"
