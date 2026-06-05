## ADDED Requirements

### Requirement: 悲观vs乐观双角色整体组合压测
系统 SHALL 对通过风控的整体组合方案执行压力测试，悲观Risk Director和乐观Risk Analyst各自分析，风控裁判综合输出。

#### Scenario: 双角色辩论输出综合评估
- **GIVEN** 风控通过的完整组合方案（含所有行业PM结果）
- **WHEN** Risk Director双角色辩论（2轮）
- **THEN** 输出：max_drawdown_20pct（市场下跌20%时最大回撤）、black_swan_trigger（触发条件列表）、cash_buffer_suggestion、悲观/乐观视角各自完整分析、风控裁判综合意见

#### Scenario: 悲观视角发现集中风险（Edge Case）
- **GIVEN** 组合中科技行业占25%，且科技行业内3只标的高度相关
- **WHEN** 悲观Risk Director分析
- **THEN** 悲观视角标注"科技行业内部相关性高，实际分散效果弱于表面"，建议降低科技配额或换入相关性低的标的

### Requirement: 压测结果不强制修改处方
Risk Director 输出 SHALL 仅为建议，不强制打回PM方案；用户可参考风险提示自行决策。

#### Scenario: 高风险方案继续执行
- **GIVEN** 悲观视角显示方案在市场下跌20%时回撤达25%（超过用户风险承受）
- **WHEN** 风控裁判综合输出
- **THEN** 在处方中显著标注风险警示，但不打回PM重做；用户可看到风险提示后选择是否执行
