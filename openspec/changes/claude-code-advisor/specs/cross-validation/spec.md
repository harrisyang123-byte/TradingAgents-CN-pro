## ADDED Requirements

### Requirement: Tier1 矛盾检测
系统 SHALL 检测同一标的的多份 Tier1 报告方向矛盾，并向 CIO 报告。

#### Scenario: 同标的多份报告方向矛盾
- **GIVEN** 000063 中兴通讯有 3 份 Tier1 报告：1 份"买入"+2 份"卖出"
- **WHEN** 交叉验证层执行
- **THEN** 系统输出 `{"code": "000063", "type": "tier1_conflict", "severity": "high"}` 到 conflicts.json
- **AND** CIO Agent 的输入中包含此冲突信息
- **AND** CIO 终裁的 `cio_verdict` 中必须说明如何处理此矛盾

### Requirement: PE 分位 vs 建议方向一致性检查
系统 SHALL 检测 PE 分位与建议方向的不一致并报告。

#### Scenario: PE 高估但建议买入
- **GIVEN** 某标的 PE 处于历史 90%+ 分位，但分析师建议买入
- **WHEN** 交叉验证层执行
- **THEN** 系统输出 `{"type": "pe_overvalued", "severity": "medium"}` 到 conflicts.json

### Requirement: 敞口重叠识别
系统 SHALL 检测基金穿透后的隐形集中度。

#### Scenario: 多只基金持有同一底层标的
- **GIVEN** 3 只 ETF 全部持有海康威视，合计暴露 > 2%
- **WHEN** 交叉验证层执行
- **THEN** 系统输出 `{"type": "overlap", "code": "002415", "total": 1.7, "sources": ["012733", "012734"]}` 到 conflicts.json

### Requirement: 黑天鹅预警检测
系统 SHALL 检测市场极端事件并预警。

#### Scenario: 三条规则同时触发
- **GIVEN** 涨跌比 < 25% + 北向连续 ≥ 5 日净流出 + 融资余额周降幅 > 5%
- **WHEN** 交叉验证层执行
- **THEN** 系统输出 `{"type": "black_swan", "severity": "high"}` 到 conflicts.json
- **AND** CIO 处方中插入"黑天鹅预警：建议保持现金缓冲 ≥ 20%"段落

#### Scenario: 行业级黑天鹅
- **GIVEN** 某行业整体跌幅 > 10% + 资金流出 > 5% + 用户该行业敞口 > 15%
- **WHEN** 交叉验证层执行
- **THEN** 系统输出 `{"type": "sector_black_swan", "severity": "high", "industry": "xxx"}` 到 conflicts.json
- **AND** 处方中该行业标的全部标注"黑天鹅风险"

### Requirement: 情绪 vs 基本面方向冲突
系统 SHALL 检测市场情绪与分析师建议的方向冲突，并标注为逆向机会而非卖出信号。

#### Scenario: 北向流出 + 推买入
- **GIVEN** 北向连续 5 日净流出，但分析师建议买入通信设备
- **WHEN** 交叉验证层执行
- **THEN** 系统不标为"冲突"——标为"逆向购买机会"
- **AND** CIO 采纳作为 immediate 处方的置信度加分项
