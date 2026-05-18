## ADDED Requirements

### Requirement: Flat-file TradingMemoryLog
系统 SHALL 使用原版的 `TradingMemoryLog` 类（append-only markdown 日志），而非 ChromaDB。

#### Scenario: 记忆存储
- **WHEN** 分析完成后保存记忆
- **THEN** 以 markdown 格式追加写入本地文件，不依赖 ChromaDB

#### Scenario: 记忆读取
- **WHEN** 新一轮分析开始
- **THEN** 从 markdown 文件读取历史记忆，返回文本格式

### Requirement: PM-only 记忆注入
记忆 SHALL 仅注入 Portfolio Manager（通过 `past_context` state 字段），不注入其他 4 个 agent。

#### Scenario: Portfolio Manager 获取历史
- **WHEN** Portfolio Manager 生成最终裁决
- **THEN** prompt 中包含 `past_context` 字段提供的历史教训

#### Scenario: 其他 agent 不注入记忆
- **WHEN** Bull Researcher / Bear Researcher / Trader / Research Manager 运行
- **THEN** 这些 agent 的 prompt 中不包含历史记忆注入

### Requirement: 移除 ChromaDB 依赖
系统 SHALL NOT 依赖 `chromadb` 包。

#### Scenario: 依赖清单
- **WHEN** 检查 `requirements.txt` 或 `pyproject.toml`
- **THEN** 不包含 `chromadb` 依赖项
