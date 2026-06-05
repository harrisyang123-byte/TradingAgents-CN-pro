# 决策层重构（decision-layer-rebuild）

**变更**: decision-layer-rebuild
**日期**: 2026-06-05
**前置**: [行业层重构](industry-layer-rebuild.md)

## 概述

将组合决策层的架构从"CIO全能"重构为职责分离的并行架构，包含并行行业PM、约束传递链、事前风控、Risk Director双角色辩论、Portfolio Synthesizer。

**核心变化**：所有需要 LLM 判断的 Agent 都用 `.md` 文件定义 + Workflow `agent()` 子 Agent 模式，取代之前的 `llm.ainvoke()` Python 代码。

## 架构变化

```
旧：L1 → L2 → L3 → CIO(选股+定权重+处方) → Risk Director(事后)
新：行业层 → 并行行业PM(每行业独立子Agent) → 风控规则引擎(事前硬拦截) → Risk Director双角色辩论 → Portfolio Synthesizer(验证+合成)
```

## 关键组件

### 约束传递链
- `total_weight_limit` 从宏观裁判输出，逐层硬传递到行业层→PM层
- 各层输出满足上游约束（不满足则打回）
- Portfolio Synthesizer 验证约束链完整性

### 并行行业PM（子Agent模式）
- `agents/advisor/v3-pm-aggressive.md`：激进PM agent定义
- `agents/advisor/v3-pm-conservative.md`：保守PM agent定义
- `agents/advisor/v3-pm-judge.md`：PM裁判 agent定义
- `scripts/workflow-v3-pm-debate.js`：Workflow 编排（pipeline：激进→保守→裁判）
- 每个Go行业独立spawn，上下文聚焦（3-5只标的）
- 买入区间：Tier1估值区间 ∩ PE30分位区间，取保守值

### 事前风控规则引擎（`risk_rules.py`）
- 四项硬约束：单股上限 / 行业上限 / 总仓位上限 / 现金下限
- 非LLM确定性检查，违规打回PM重做
- `auto_truncate`：第3次违规时强制截断

### Risk Director 双角色
- `v3-risk-pessimist.md`：悲观视角，找最坏情景
- `v3-risk-optimist.md`：乐观视角，挑战悲观假设
- `v3-risk-judge.md`：综合双方输出最终风险评估

### Portfolio Synthesizer
- `v3-portfolio-synthesizer.md`：替代原CIO Final
- 验证约束链完整性（不修正，只报警）
- 识别行业缺口（gap>3%触发补充侦察）
- 输出 industry_matrix + final_prescription
- 不是CIO——不选股、不定权重、不做新判断

### /overview 简化
- 优先读最近一次 advice 的 industry_matrix/synthesis_result
- 无 v3 数据时降级到 v2 拼接逻辑（向后兼容）
- 删除 classify_llm 运行时调用

## 子Agent模式规范

Agent 逻辑必须走：
1. `agents/advisor/v3-{name}.md` — system prompt + JSON schema + tools
2. `scripts/workflow-v3-{name}.js` — 用 `agent()` 调用子 Agent
3. 数据通过 JSON 文件在步骤间传递

**绝对禁止**：`llm.ainvoke()` / `asyncio.new_event_loop()` （历史教训，详见 memory）

## 注意事项

- `.md` agent 文件中的 `{variable}` 占位符在工作流脚本中拼接替换，确保不冲突
- 风控违规时 Workflow 返回 violations 列表，由编排层处理打回逻辑
- 现有 `cio.py` 保留未删除（向后兼容），v3 新流程通过 Workflow 独立执行
- 变更1遗留的 `industry_researcher.py` / `cross_industry_judge.py` 仍用 `llm.ainvoke()`，不影响新流程但建议后续清理
