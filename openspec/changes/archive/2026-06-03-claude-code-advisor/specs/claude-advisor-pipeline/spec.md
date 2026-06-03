## ADDED Requirements

### Requirement: 9 个子 Agent 四层分析管线
系统 SHALL 通过 Python 主控脚本编排 9 个独立子 Agent，通过 JSON 文件总线传递完整上下文。每个子 Agent 一次独立的 LLM 调用。

#### Scenario: 全链路执行
- **WHEN** 用户运行 `python cli/claude_advisor.py --user-id 6a094caea814b57d3357fa0b`
- **THEN** 系统依次执行数据收集 → L1 行业方向(3 Agent 2 轮辩论) → L2 标的筛选(1 Agent + 交叉验证) → L3 组合诊断(2 Agent 2 轮辩论) → L4 最终处方(3 Agent 1 轮辩论) → 保存 MongoDB
- **AND** 每步输出写入 `/tmp/claude_advisor/` 下的 JSON 文件
- **AND** 最终写入 MongoDB `portfolio_advice` (source='claude-code-v3')

#### Scenario: 数据收集失败容错
- **WHEN** AKShare 连接超时导致基金净值获取失败
- **THEN** 系统记录警告、跳过失败数据项、继续执行剩余管线
- **AND** 失败数据项在最终处方中标注"数据不可用"

#### Scenario: 单次分析性能
- **WHEN** 用户触发全链路分析
- **THEN** 系统在 5 分钟内完成（含 9 次 LLM 调用 + 数据收集）
