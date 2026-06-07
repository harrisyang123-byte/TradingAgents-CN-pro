# v4-non-equity-plans Specification

## Purpose
为固定收益/现金及等价物/大宗商品/贵金属/房地产/另类投资六大类，按该资产本质给出与其下钻深度匹配的差异化投资方案，而非套用权益的「行业→个股」结构。复用大类研究部门范式。对应 FR-007。

## Requirements

### Requirement: 非权益专属分析部门
系统 SHALL 对每个非权益大类运行其专属分析部门（多轮辩论 + 总监拍板，复用大类研究部门范式），输出该类的方向研判与投资方案；方案单元 `plan:<class>` 同样遵守单元独立触发与快照指纹/软提醒机制。

#### Scenario: 非权益方案单元运行
- **GIVEN** 触发 `analyze plan:fixed_income`
- **WHEN** 部门运行
- **THEN** 产出 verdict + 固收专属方案，并落 `data/v4/plans/fixed_income.json`

### Requirement: 现金及等价物持有结构方案
系统 SHALL 为现金及等价物产出「持有结构方案」，在活期/货币基金/短期国债/逆回购等工具间给出建议分布与理由（持有型，不推荐个券）。

#### Scenario: 现金持有结构
- **WHEN** 运行 `plan:cash`
- **THEN** payload `holding_structure[]` 给出各工具建议分布 + 理由，不含个券推荐

### Requirement: 固定收益久期与品种结构
系统 SHALL 为固定收益产出久期与品种结构建议（国债/信用债/可转债/债基的配比与久期取向），结合利率环境。

#### Scenario: 固收久期方案
- **WHEN** 运行 `plan:fixed_income`
- **THEN** payload 含 `duration_view` + `instrument_mix[]`

### Requirement: 大宗与贵金属品种工具方案
系统 SHALL 为大宗商品、贵金属产出品种/工具层方案（如贵金属在实物/黄金 ETF/金矿股间取向；大宗在能源/工业金属/农产品间取向），可交易工具可下钻，纯持有型仅记敞口。

#### Scenario: 贵金属工具取向
- **WHEN** 运行 `plan:precious_metal`
- **THEN** payload `instrument_mix[]` 含实物/ETF/金矿股取向，可交易 tradable、持有型记敞口

### Requirement: 房地产 REITs 下钻与实物记敞口
系统 SHALL 对可交易的 REITs 下钻到工具层方案；对实物房产仅作为配置桶记录敞口、给出宏观层面持有建议。

#### Scenario: 房地产差异化
- **WHEN** 运行 `plan:real_estate`
- **THEN** REITs 进 tradable 工具方案，实物房产入 holding_only + 宏观持有建议

### Requirement: 另类品种方案与风险标注
系统 SHALL 对另类投资（虚拟币等）给出品种层方案，并显著标注高波动/合规风险。

#### Scenario: 另类风险标注
- **WHEN** 运行 `plan:alternative`
- **THEN** payload `instrument_mix[]` + 显著 `risk_flags[]`（高波动/合规）
