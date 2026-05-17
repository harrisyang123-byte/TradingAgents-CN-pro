## ADDED Requirements

### Requirement: 组合建议触发入口
系统 SHALL 在"我的持仓"页面提供触发组合建议的入口。

#### Scenario: 点击获取建议
- **WHEN** 用户在持仓页面点击"组合建议"按钮
- **THEN** 系统调用 POST /api/portfolio/advice，按钮显示加载状态，显示进度提示

#### Scenario: 无持仓时
- **WHEN** 用户无任何持仓，点击"组合建议"
- **THEN** 提示"请先录入持仓后再获取组合建议"

#### Scenario: 生成中再次点击
- **WHEN** 组合建议正在生成中，用户再次点击按钮
- **THEN** 按钮显示禁用状态，提示"正在生成中"

### Requirement: 组合建议展示面板
系统 SHALL 在持仓页面以抽屉（el-drawer）形式展示组合建议结果。

#### Scenario: 展示处方
- **WHEN** 组合建议生成完成
- **THEN** el-drawer 自动打开，展示处方表格：标的代码 | 品种图标 | 操作（颜色标记）| 幅度 | 理由。新建仓条目特殊标注，过期报告 ⚠️ 标注

#### Scenario: 展示辩论记录
- **WHEN** 用户点击"查看辩论过程"
- **THEN** 折叠面板展开，按角色分 Tab 显示：分析师 / 策略师 / 侦察兵 / CIO 裁定

#### Scenario: 查看历史建议
- **WHEN** 用户在面板中选择历史日期
- **THEN** 面板切换显示该日期的组合建议内容

#### Scenario: 操作颜色标记
- **WHEN** AdviceItem 的操作类型为 BUY 或 ADD
- **THEN** 操作文字显示为红色（A 股惯例红涨）
- **WHEN** AdviceItem 的操作类型为 SELL 或 REDUCE
- **THEN** 操作文字显示为绿色
- **WHEN** AdviceItem 的操作类型为 HOLD 或 WATCH
- **THEN** 操作文字显示为灰色
