## MODIFIED Requirements

### Requirement: CIO 处方结构升级
CIO 最终输出 SHALL 包含三个新区段：

#### Scenario: 敞口诊断
- **WHEN** CIO 输出 `cio_verdict`
- **THEN** 第一部分 SHALL 为"敞口诊断"：基金穿透后的真实底层暴露、隐形重仓标的的权重合计、穿透覆盖率
- **AND** 直接持股与基金底层持股的重叠暴露 SHALL 被列出

#### Scenario: 资金分配方案
- **WHEN** CIO 输出处方
- **THEN** 每条 BUY/ADD/new_position 处方 SHALL 包含 `capital_source` 字段
- **AND** Σ 买入金额 ≤ 可用现金 + Σ 卖出释放金额
- **AND** 如果资本来源不充分，处方 SHALL 只包含资金来源可覆盖的操作数

#### Scenario: CIO 终裁角色
- **WHEN** CIO 初稿 + 风险总监审查产生后
- **THEN** CIO 终裁 SHALL 在 `cio_verdict` 中说明：(1) 采纳了哪些风险意见，(2) 拒绝了哪些（附理由），(3) 最终处方
- **AND** 处方 SHALL 覆盖全部持仓（含现金）

### Requirement: CIO 处方含市场水温参考
CIO 终裁 SHALL 基于全市场水温判定 timing。

#### Scenario: 恐慌市场下的 timing 判断
- **WHEN** 市场涨跌比 < 25% + 北向连续流出
- **THEN** 基本面 Go 的标的 timing 倾向 `immediate`
- **AND** CIO 在处方中标注"市场恐慌下的逆向买入"
