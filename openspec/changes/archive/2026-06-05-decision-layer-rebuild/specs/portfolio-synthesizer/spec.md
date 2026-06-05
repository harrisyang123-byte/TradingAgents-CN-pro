## ADDED Requirements

### Requirement: 验证约束传递链完整性
Portfolio Synthesizer SHALL 验证约束从宏观到行业到PM的传递是否完整，发现断裂时报警标注，不静默修正。

#### Scenario: 约束链完整通过验证
- **GIVEN** 所有行业PM的个股加总均在行业final_weight内，所有行业加总在total_weight_limit内
- **WHEN** Portfolio Synthesizer验证
- **THEN** constraint_chain_valid=true，violations=[]，流程继续

#### Scenario: 发现约束断裂报警（Edge Case）
- **GIVEN** 科技行业PM个股加总28%，超过final_weight=25%
- **WHEN** Portfolio Synthesizer验证
- **THEN** constraint_chain_valid=false，violations=["科技行业PM超出配额3%"]，对应处方标注"约束异常，请人工复核"，不自动修正

### Requirement: 缺口处理与补充侦察触发
Portfolio Synthesizer SHALL 识别行业配额未填满的缺口，计算缺口大小，触发 dispatch_scout 补充侦察。

#### Scenario: 触发缺口侦察
- **GIVEN** 科技行业 final_weight=25%，PM实际配仓=14%，缺口=11%
- **WHEN** Portfolio Synthesizer处理缺口
- **THEN** 在 industry_matrix 中标注 gap=11%，触发 dispatch_scout 搜索科技行业更多候选标的，gap_scout_triggered=true

#### Scenario: 缺口过小不触发侦察
- **GIVEN** 消费行业缺口=1.5%（< 阈值3%）
- **WHEN** Portfolio Synthesizer处理缺口
- **THEN** 缺口标注在矩阵中，不触发侦察（过小缺口留为现金缓冲合理）

### Requirement: 汇总输出完整处方和行业矩阵
Portfolio Synthesizer SHALL 汇总所有行业PM结果和行业矩阵，输出用户可直接执行的最终处方。

#### Scenario: 处方包含完整执行信息
- **WHEN** Portfolio Synthesizer输出最终处方
- **THEN** 每条处方包含：code/name/industry/action/current_weight/target_weight/entry_price_range/build_strategy/batch_plan/reasoning/risk_note；行业矩阵每行包含：industry/source/go_nogo/vitality_level/final_weight/actual_weight/gap
