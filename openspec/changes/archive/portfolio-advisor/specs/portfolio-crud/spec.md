## ADDED Requirements

### Requirement: 单账户持仓管理
系统 SHALL 提供单账户模式管理用户真实持仓，统一人民币计价，支持 A 股/港股/美股三个市场。

#### Scenario: 创建持仓（CLI 录入）
- **WHEN** 用户通过 API 提交 `POST /api/portfolio/positions` 包含 `{code: "600519", quantity: 1000, avg_cost: 1850, buy_date: "2024-03-15"}`
- **THEN** 系统创建 Position 记录，自动识别市场为 CN，创建 Transaction 记录（side=buy）

#### Scenario: 创建持仓（Web 手动录入）
- **WHEN** 用户在前端"添加持仓"弹窗填写代码/数量/价格/日期并提交
- **THEN** 系统调用同一 API 创建 Position，行为与 CLI 录入一致

#### Scenario: 追加买入已有持仓
- **WHEN** 用户提交 `POST /api/portfolio/positions` 的 code 已存在
- **THEN** 系统以加权平均计算新 avg_cost：`(old_cost × old_qty + new_price × new_qty) / (old_qty + new_qty)`，创建 Transaction 记录

#### Scenario: 修改持仓
- **WHEN** 用户提交 `PUT /api/portfolio/positions/{code}` 包含 `{quantity: 500, avg_cost: 1900}`
- **THEN** 系统更新 Position 对应字段，创建 Transaction 记录

#### Scenario: 删除持仓
- **WHEN** 用户提交 `DELETE /api/portfolio/positions/{code}`
- **THEN** 系统删除该 Position 记录

#### Scenario: 卖出持仓
- **WHEN** 用户提交 `POST /api/portfolio/order` 包含 `{code: "600519", side: "sell", quantity: 500, price: 1950}`
- **THEN** 系统减少 Position 数量，增加 available_cash（`quantity × price`），创建 Transaction 记录

#### Scenario: 卖出数量超过持有
- **WHEN** 用户提交卖出数量 > 当前持仓数量
- **THEN** 系统返回 400 错误 "卖出数量超过持仓"

### Requirement: 账户总投入与可用现金
系统 SHALL 记录用户的总投入资金和可用现金（均为人民币），用于计算总盈亏。

#### Scenario: 设置账户资金
- **WHEN** 用户提交 `PUT /api/portfolio/account` 包含 `{total_invested: 300000, available_cash: 50000}`
- **THEN** 系统更新 PortfolioAccount 对应字段

#### Scenario: 查看账户信息
- **WHEN** 用户提交 `GET /api/portfolio/account`
- **THEN** 系统返回 total_invested、available_cash、总资产、总盈亏、总盈亏率

### Requirement: 组合总览
系统 SHALL 提供组合级汇总数据，包括仓位分布和盈亏计算。

#### Scenario: 查看组合总览
- **WHEN** 用户提交 `GET /api/portfolio/summary`
- **THEN** 系统返回：总资产（持仓市值CNY + 可用现金）、总投入、总盈亏、总盈亏率、每只持仓的市值/仓位占比/盈亏率

#### Scenario: 港股/美股市值折算
- **WHEN** 持仓中有港股或美股
- **THEN** 系统按中国银行外汇牌价（`currency_boc_safe`）将市值折算为人民币

#### Scenario: 无持仓时查看总览
- **WHEN** 用户无任何持仓
- **THEN** 系统返回空持仓列表 + 账户信息（total_invested 和 available_cash）

### Requirement: 总盈亏计算
系统 SHALL 按公式 `总盈亏 = (持仓市值 + 可用现金) - 总投入` 计算盈亏，自然包含已实现和未实现盈亏。

#### Scenario: 正常计算
- **WHEN** 用户总投入 300000，可用现金 50000，持仓市值 280000
- **THEN** 总盈亏 = (280000 + 50000) - 300000 = 30000，盈亏率 = 10%
