# position-industry-classifier Specification

## Purpose
TBD - created by archiving change industry-layer-rebuild. Update Purpose after archive.
## Requirements
### Requirement: 持仓录入时同步写入行业分类
系统 SHALL 在用户录入或更新持仓时，自动调用行业分类逻辑写入 paper_positions.industry，不依赖运行时 LLM 实时分类。

#### Scenario: 新增持仓时自动分类
- **GIVEN** 用户录入股票代码 600519（贵州茅台）
- **WHEN** 持仓保存
- **THEN** 系统自动将 industry 字段写入"白酒/食品饮料"，用户无需手动选择

#### Scenario: 更新持仓时行业字段同步更新
- **GIVEN** 用户修改某持仓的数量或成本
- **WHEN** 持仓更新保存
- **THEN** industry 字段保持不变（不重新分类），除非用户手动修改了股票代码

#### Scenario: 行业分类失败时的降级（Edge Case）
- **GIVEN** LLM 行业分类接口超时（持仓录入时）
- **WHEN** 系统尝试写入 industry 字段
- **THEN** industry 字段写入"未分类"，持仓正常保存，后台异步补充分类，不阻断用户操作

### Requirement: 历史持仓行业字段补填
系统 SHALL 提供一次性迁移机制，为 industry 字段为空的历史持仓补填行业分类。

#### Scenario: 迁移脚本补填历史数据
- **GIVEN** 数据库中存在 industry 字段为空的历史持仓记录
- **WHEN** 执行迁移脚本
- **THEN** 所有空 industry 字段被批量补填，补填失败的记录标记为"未分类"，输出迁移报告

