# industry-debate-cache Specification

## Purpose
TBD - created by archiving change industry-layer-rebuild. Update Purpose after archive.
## Requirements
### Requirement: 7天有效期缓存复用
系统 SHALL 在行业研究员运行前检查 industry_coverage 缓存，未过期（7天内）的行业直接复用结论，跳过重新辩论。

#### Scenario: 缓存命中直接复用
- **GIVEN** 科技行业3天前已辩论，expires_at 未到期
- **WHEN** 新一轮分析启动
- **THEN** 科技行业跳过研究员和辩论，直接读取缓存的 go_nogo + suggested_weight，耗时 < 1秒

#### Scenario: 缓存过期重新运行
- **GIVEN** 消费行业8天前已辩论，expires_at 已过期
- **WHEN** 新一轮分析启动
- **THEN** 消费行业触发完整研究员 + 辩论流程，完成后更新 expires_at = now + 7天

#### Scenario: 手动强制刷新（Edge Case）
- **GIVEN** 用户在界面点击"强制刷新科技行业"
- **WHEN** 系统处理刷新请求
- **THEN** 科技行业缓存立即失效，下次分析时触发完整辩论，其他行业缓存不受影响

### Requirement: industry_coverage 集合 schema 升级
系统 SHALL 升级 industry_coverage 集合，新增 suggested_weight、expires_at、debate_history、vitality_score 字段。

#### Scenario: 新记录包含完整字段
- **WHEN** 行业辩论完成写入 industry_coverage
- **THEN** 记录包含：go_nogo、suggested_weight（0-1浮点）、expires_at（ISO时间戳）、debate_history（辩论完整文本）、vitality_score（景气打分）、reasoning、lifecycle

#### Scenario: 历史记录兼容迁移（Edge Case）
- **GIVEN** 数据库中存在不含 expires_at 字段的旧记录
- **WHEN** 系统读取旧记录判断是否过期
- **THEN** 缺少 expires_at 的记录视为已过期，触发重新研究，不报错不崩溃

