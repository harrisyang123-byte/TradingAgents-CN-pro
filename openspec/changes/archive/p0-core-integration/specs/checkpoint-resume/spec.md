## ADDED Requirements

### Requirement: 每 ticker 断点持久化

系统 SHALL 提供每 ticker 级别的 checkpointer，使用 SqliteSaver 持久化 graph 状态。

#### Scenario: 正常 checkpoint 保存
- **WHEN** graph 每完成一个节点执行
- **THEN** 当前状态写入 .checkpoints/ 目录下的 SQLite 数据库
- **AND** 每个 ticker 使用独立 thread_id

#### Scenario: 从断点恢复
- **WHEN** 重新运行之前中断过的 ticker
- **THEN** 从上次保存的状态继续执行
- **AND** 跳过已完成的节点

### Requirement: 配置控制 checkpoint 启用

checkpoint SHALL 默认关闭，通过配置控制启用。

#### Scenario: 默认关闭
- **GIVEN** 系统初始配置
- **WHEN** 启动分析
- **THEN** 不创建 checkpoint 文件
- **AND** 不影响现有分析流程

#### Scenario: 启用 checkpoint
- **WHEN** checkpoint_enabled = True
- **THEN** 每个 ticker 分析前创建 checkpointer
- **AND** 分析完成后 checkpoint 文件保留在磁盘

### Requirement: 文件损坏容错

checkpointer SHALL 在文件损坏时优雅降级而不崩溃。

#### Scenario: 损坏的 checkpoint 文件
- **GIVEN** .checkpoint 文件已损坏
- **WHEN** 尝试从断点恢复
- **THEN** 记录警告日志
- **AND** 从头开始运行分析
