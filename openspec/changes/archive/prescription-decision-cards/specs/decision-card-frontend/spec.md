# Spec: Decision Card Frontend

## ADDED Requirements

### Requirement: Vertical Card Stream Layout
The PaperTrading drawer SHALL replace the flat `el-table` with a vertical decision card stream, with cards ordered by priority (urgent > important > optional) and color-coded left borders indicating urgency level.

#### Scenario: 卡片按优先级排序
- **GIVEN** CIO 返回 urgent/important/optional 不同优先级的处方
- **WHEN** 前端渲染决策卡片
- **THEN** urgent 卡片置顶（红色左边框），important 次之（橙色），optional 在底部（灰色）

#### Scenario: 卡片默认状态
- **GIVEN** 用户打开组合顾问抽屉
- **WHEN** 处方首次渲染
- **THEN** 每条卡片显示 header + suggested_price 行 + risk 摘要行。l1_context 和 l2_context 默认收起，点击展开。

#### Scenario: 卡片展开查看上下文
- **GIVEN** 卡片处于收起状态
- **WHEN** 用户点击展开按钮
- **THEN** 显示完整的 l1_context、l2_context 以及完整 reasoning

### Requirement: PE Percentile Visual Indicator
The DecisionCard component SHALL render a three-color progress bar (green=undervalued 0-25%, yellow=fair 25-75%, red=overvalued 75-100%) when PE percentile data is available, and MUST hide the progress bar when PE percentile is unavailable.

#### Scenario: PE 分位进度条
- **GIVEN** suggested_price 文本中包含 PE 分位数据
- **WHEN** 卡片渲染
- **THEN** 显示分位进度条——绿色(0-25%)=低估，黄色(25-75%)=合理，红色(75-100%)=高估

#### Scenario: PE 分位不可用
- **GIVEN** suggested_price 不包含 PE 分位数据（如美股或新股）
- **WHEN** 卡片渲染
- **THEN** 不显示进度条，仅显示文本判断

### Requirement: Risk Row
The DecisionCard component SHALL display a risk summary row containing max_loss_pct, five_year_view summary, and bias_check result at the bottom of each card.

#### Scenario: 风险行展示
- **GIVEN** 卡片渲染
- **WHEN** 展示 risk 行
- **THEN** 显示 `max_loss_pct`（如 "最大亏损 -15%"）+ `five_year_view`（是/否 + 理由摘要）+ `bias_check`（检测到偏差时高亮）

### Requirement: Edge Case — 部分字段缺失
The DecisionCard component MUST gracefully handle missing optional fields (max_loss_pct, bias_check, five_year_view) by displaying an em-dash placeholder without breaking the card layout or causing render errors.

#### Scenario: 缺失可选字段不破坏布局
- **GIVEN** 某条处方缺少 `max_loss_pct` 或 `bias_check`（CIO 未输出）
- **WHEN** 卡片渲染
- **THEN** 对应行显示 "—"，卡片不崩溃，布局不变
