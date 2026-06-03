## MODIFIED Requirements

### Requirement: L2 Scout 基于 L1 方向 + 财务数据引用
Scout SHALL 从 L1 裁判的 Go 行业列表开始搜索，而非全市场盲扫。每只候选 MUST 附带有具体数值的财务数据（ROE、营收增速、FCF、负债率），MUST 包含 `pricing_range` 格式的价格区间（¥XX-YY），MUST 包含催化剂和 `target_position`。≥30% 的候选 SHALL 来自中市值(市值<500亿)或增速>20%的公司。

#### Scenario: 基于 L1 行业搜索
- **WHEN** L1 裁判输出超配方向为"通信设备"
- **THEN** Scout 优先搜索通信设备行业成分股
- **AND** 不推荐 L1 裁定为零配的行业中的标的

#### Scenario: 财务数据引用
- **WHEN** Scout 输出任一候选标的
- **THEN** 输出 SHALL 包含 `financial_data: {roe, revenue_growth, fcf, debt_ratio, pe_current}` 子结构
- **AND** 每个字段不得为空字符串（如数据不可用，标注 "N/A" 而非省略）

#### Scenario: 中市值覆盖
- **WHEN** Scout 输出候选池
- **THEN** 至少 30% 的候选 SHALL 来自市值 < 500 亿人民币 或 年营收增速 > 20%
- **AND** 如果无法满足，输出中 SHALL 标注原因（如"通信设备行业 A 股上市公司最低市值已在 500 亿以上"）
