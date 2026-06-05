## ADDED Requirements

### Requirement: 行业 Go 结果自动触发 Tier1 研究
系统 SHALL 在行业层输出 Go 结论后，自动触发该行业主要公司的 Tier1 研究，结果写入研究库供下游消费。

#### Scenario: Go 行业自动触发公司研究
- **GIVEN** 行业辩论裁判输出科技行业 go_nogo=Go
- **WHEN** 行业层完成
- **THEN** 系统自动识别科技行业主要公司（市值前10），对未缓存或缓存过期的公司触发 Tier1 研究，异步执行不阻塞主流程

#### Scenario: NoGo 行业不触发研究
- **GIVEN** 行业辩论裁判输出地产行业 go_nogo=NoGo
- **WHEN** 行业层完成
- **THEN** 系统不触发地产行业公司研究，节省 token 消耗

#### Scenario: Tier1 研究结果存库供下游取用
- **WHEN** Tier1 研究完成
- **THEN** 结果写入研究库（含评级/目标价/买入区间/有效期7天），Step2 公司层和 Step3 组合层可直接读取，不重复研究

#### Scenario: 研究库缓存命中（Edge Case）
- **GIVEN** 中兴通讯3天前已有 Tier1 研究报告，未过期
- **WHEN** 科技行业判 Go，触发公司研究
- **THEN** 中兴通讯直接复用缓存报告，不重新运行 Tier1，其他未缓存公司正常研究

### Requirement: Tier1 不再作为独立用户触发工具
Tier1 研究 SHALL 主要由行业层驱动，用户仍可手动触发单只股票分析，但手动触发结果同样写入研究库。

#### Scenario: 手动触发结果写入研究库
- **GIVEN** 用户在个股分析页面手动分析茅台
- **WHEN** Tier1 研究完成
- **THEN** 结果写入研究库（与自动触发结果同库），下次组合分析时 Step2/PM 可直接复用
