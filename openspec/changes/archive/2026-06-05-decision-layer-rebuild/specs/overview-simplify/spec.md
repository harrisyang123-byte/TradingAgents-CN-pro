## ADDED Requirements

### Requirement: /overview 数据源切换为 advice.industry_matrix
系统 SHALL 将 `/paper/overview` 接口的行业矩阵数据源从实时拼接改为直接读取最近一次 portfolio_advice 的 industry_matrix 字段。

#### Scenario: 读取最近一次advice的industry_matrix
- **GIVEN** 用户有一次状态为COMPLETED的portfolio_advice记录
- **WHEN** 调用 GET /paper/overview
- **THEN** 行业矩阵数据来自 advice.industry_matrix，不再调用 classify_llm，响应时间减少≥2秒

#### Scenario: 无advice记录时降级展示（Edge Case）
- **GIVEN** 用户从未运行过组合分析
- **WHEN** 调用 GET /paper/overview
- **THEN** 返回空矩阵，提示"请先运行组合分析"，不报错

### Requirement: 行业矩阵新增列展示
系统 SHALL 在前端行业矩阵表格中新增：vitality_level（景气强度）、gap（配额缺口）、source（入池来源）列。

#### Scenario: 新增列正确展示
- **WHEN** 用户查看行业矩阵
- **THEN** 每行显示：vitality_level（强烈看好/看好/中性/看空）、gap（行业配额与实际配仓的差额，正数=缺口，负数=超配）、source（holding/watchlist/vitality）

#### Scenario: 处方详情新增执行信息（Edge Case）
- **GIVEN** 用户点击某条处方查看详情
- **WHEN** 详情抽屉展示
- **THEN** 显示：entry_price_range（买入价格区间）、build_strategy（立即/分批/条件）、batch_plan（若分批：各批次价格和仓位）、tier1_rating（Tier1评级来源）、pe_percentile（PE分位）
