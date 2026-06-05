## ADDED Requirements

### Requirement: 约束从宏观层硬传递到行业层再到PM层
系统 SHALL 将宏观裁判输出的 total_weight_limit 和 cash_floor 作为硬约束注入行业层和PM层，每层输出必须满足上游约束。

#### Scenario: 约束传递链完整执行
- **GIVEN** 宏观裁判输出 total_weight_limit=60%, cash_floor=15%
- **WHEN** 行业层跨行业裁判分配 final_weight
- **THEN** 所有行业 final_weight 加总 ≤ 60%，PM层个股 target_weight 加总天然不超60%

#### Scenario: 行业层资源分配而非归一化
- **GIVEN** total_weight_limit=60%，3个Go行业景气强度：科技=强烈看好，消费=看好，医药=中性
- **WHEN** 跨行业裁判分配 final_weight
- **THEN** 科技获得最多配额（如25%），消费次之（20%），医药最少（15%），加总=60%；不是各行业独立权重归一化

#### Scenario: 约束断裂时报警（Edge Case）
- **GIVEN** 某行业PM输出的个股 target_weight 加总 > 该行业 final_weight（约束未被正确接收）
- **WHEN** Portfolio Synthesizer验证约束链
- **THEN** 标注违规行业和超出金额，报警给用户，不静默修正；该行业处方标记为"约束异常，请人工复核"
