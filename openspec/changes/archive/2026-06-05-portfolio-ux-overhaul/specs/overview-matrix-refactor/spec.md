## ADDED Requirements

### Requirement: 行业配置矩阵展示
系统 SHALL 在组合总揽页面展示行业配置矩阵，每行显示：行业名 | 当前→目标仓位 | 景气强度 | 生命周期 | 操作建议（¥净买入/净卖出/持仓不动）。

#### Scenario: 行业矩阵正常展示
- **GIVEN** overview 包含行业矩阵数据
- **WHEN** 用户打开组合总揽页面
- **THEN** 展示行业列表（排除"现金"行），每行显示当前仓位→目标仓位的百分比对比、景气强度标签、生命周期标签、操作金额

#### Scenario: 无数据时展示空状态
- **GIVEN** overview 无行业矩阵数据
- **WHEN** 用户打开组合总揽页面
- **THEN** 显示"暂无配置数据"空状态提示

### Requirement: 行业详情 Drawer
系统 SHALL 在用户点击行业行时从右侧滑出 Drawer（宽 65%），展示：配置快览 → 行业分析(reasoning) → 个股处方列表。

#### Scenario: Drawer 原地刷新不闪烁
- **GIVEN** Drawer 已打开（科技行业），用户点击消费行业行
- **WHEN** selectedIndustry 赋值切换
- **THEN** Drawer 原地刷新为新行业内容，不关闭再打开

#### Scenario: reasoning 默认展开可收起
- **GIVEN** 行业有 reasoning 数据
- **WHEN** Drawer 打开
- **THEN** reasoning 通过 el-collapse-item 默认展开，用户可点击收起

### Requirement: 个股处方列表
系统 SHALL 在 Drawer 内展示该行业下个股处方 list（非卡片），列：标的名+代码 | 操作 | 当前→目标 | 买入区间 | 建仓策略 | Tier1评级 | PE分位。

#### Scenario: 扩展行展示分批计划和理由
- **GIVEN** 个股处方含 batch_plan 和 reasoning
- **WHEN** 用户点击行首的展开按钮
- **THEN** 展示完整分批计划（每批价格/仓位/条件）、完整理由、风险提示

#### Scenario: 无个股处方时（Edge Case）
- **GIVEN** 该行业无 positions_detail 数据
- **WHEN** Drawer 打开
- **THEN** 显示"该行业暂无个股处方数据"

### Requirement: 删除 Analysis 页
系统 SHALL 移除 `/portfolio/analysis` 路由和侧边栏"持仓分析"菜单项。

#### Scenario: 路由已移除
- **WHEN** 用户访问 /portfolio/analysis
- **THEN** 前端路由匹配失败，自动跳转到默认页面

#### Scenario: 侧边栏菜单项已移除
- **WHEN** 侧边栏渲染
- **THEN** 不包含"持仓分析"菜单项
