## ADDED Requirements

### Requirement: 我的持仓页面
系统 SHALL 将"模拟交易"页面改造为"我的持仓"页面，展示用户真实持仓和组合总览。

#### Scenario: 页面加载
- **WHEN** 用户访问"我的持仓"页面
- **THEN** 页面展示：账户总览（4 个统计卡片：总资产/总投入/可用现金/总盈亏率）、组合图表（仓位分布饼图）、持仓列表（含仓位占比和盈亏率列）

#### Scenario: 市场过滤
- **WHEN** 用户点击持仓列表上方的市场 Tab（全部/A股/港股/美股）
- **THEN** 持仓列表按所选市场过滤展示

#### Scenario: 空持仓
- **WHEN** 用户无任何持仓
- **THEN** 页面展示空态引导：CLI 录入命令示例 + "添加持仓"按钮

#### Scenario: 红涨绿跌
- **WHEN** 持仓盈亏为正
- **THEN** 盈亏数字显示为红色（A 股惯例）

### Requirement: 手动添加持仓弹窗
系统 SHALL 在前端提供"添加持仓"弹窗，用户手动填写持仓信息。

#### Scenario: 添加持仓
- **WHEN** 用户点击"添加持仓"按钮，在弹窗中填写代码(600519)、数量(1000)、买入价(1850)、买入日期(2024-03-15)并提交
- **THEN** 系统调用 `POST /api/portfolio/positions` 创建持仓，刷新页面数据

#### Scenario: 卖出持仓
- **WHEN** 用户点击持仓行的"卖出"按钮，填写卖出数量和卖出价格
- **THEN** 系统调用 `POST /api/portfolio/order` 处理卖出，更新持仓和可用现金

#### Scenario: 发起分析
- **WHEN** 用户点击持仓行的"分析"按钮
- **THEN** 跳转到单股分析页，带 ticker 参数

### Requirement: 路由重命名
系统 SHALL 将前端路由 `/paper` 重命名为 `/portfolio`，旧路由重定向。

#### Scenario: 访问旧路由
- **WHEN** 用户访问 `/paper`
- **THEN** 自动重定向到 `/portfolio`
