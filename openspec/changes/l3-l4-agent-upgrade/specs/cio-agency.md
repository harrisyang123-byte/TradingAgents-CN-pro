# CIO Agent 验收规格

## 1. CIO 工具调用

### 1.1 分页读持仓
- [x] CIO 先调用 `get_position_batch(1)` 获取第一批持仓和总数
- [x] 如果 `has_more=true`，继续调用 batch=2,3,4... 直到读完所有持仓
- [x] 每个标的返回完整字段：code, name, weight, market_value_cny, avg_cost, last_price, pnl_pct, health, industry

### 1.2 行业评级查询
- [x] CIO 对每个持仓标的的 `industry` 字段调用 `get_l1_verdict(industry)`
- [x] 返回 L1 评级（Go/NoGo/观察）和生命周期阶段

### 1.3 L2 候选池
- [x] CIO 调用 `get_l2_candidates()` 获取候选标的池

### 1.4 派员工搜索
- [x] `dispatch_scout(industry, market)` 调用成功返回行业 Top 10 标的
- [x] 返回数据包含 PE/ROE/营收增速/市值
- [x] 当 L2 候选池未覆盖某行业时，CIO 自动调用 dispatch_scout

### 1.5 ETF 搜索
- [x] `search_industry_etf(industry, market)` 返回相关 ETF 列表
- [x] 包含费率和规模信息

### 1.6 权重验证
- [x] `validate_allocation(json)` 检查 Σ ≤ 100%，单行业 ≤ 50%，现金 ≥ 5%
- [x] 发现违规时 CIO 修正方案后重新 validate

## 2. 处方输出

### 2.1 全量覆盖
- [x] JSON 处方列表覆盖所有现有持仓标的
- [x] action="hold" 的标的也必须列出，有维持理由
- [x] 处方数量 = 持仓数量，自适应（36 只→36 条，20 只→20 条）

### 2.2 输出格式
- [x] 第一部分：行业配置表（markdown 表格）
- [x] 第二部分：总体判断（2-3 段）
- [x] 第三部分：JSON 处方（```json 代码块）

### 2.3 处方字段
- [x] 每条处方包含：code, name, instrument_type, action, current_weight, target_weight
- [x] 扩展字段：industry_bucket, fund_role, timing, capital_source, priority
- [x] NoGo 行业对应标的目标权重为 0%

## 3. 工具调用限制

- [x] 工具调用上限 3 次（可配置）
- [x] 达上限后注入强制总结消息
- [x] 不会无限循环

## 4. Industry Allocation 输出
- [x] L1 评级为 Go 的行业在行业配置表中体现
- [x] 每个行业有当前仓位、目标仓位、配置方向
- [x] Σ 行业目标仓位 + 现金 = 100%
