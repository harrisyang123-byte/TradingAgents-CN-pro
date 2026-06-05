# OpenSpec 流程规范

> 本规则定义了 ACE 中所有变更的生命周期，确保“每一步都有据可查，每一行都有理可循”。

## 1. 核心阶段说明

### Phase 1: Explore (探索)
*   **输入**：模糊的需求或原始想法。
*   **动作**：分析可行性，调研现有代码（取长补短），界定影响范围。
*   **产出**：初步的技术方案思路或调研笔记。

### Phase 2: Plan (规划)
*   **动作**：将需求结构化为具体的 Feature 或版本目标。
*   **产出**：`planning/` 下的 Markdown 文档。

### Phase 3: Propose (提案)
*   **动作**：编写详细的设计规格（Spec）和任务分解（Tasks）。
*   **产出**：在 `openspec/changes/${change-id}/` 下创建 `proposal.md` 和 `tasks.md`。
*   **辩证要求**：必须在 proposal 中包含“方案对比”章节。

### Phase 4: Apply (实施)
*   **动作**：根据 `tasks.md` 逐项编写代码。
*   **要求**：每完成一个子任务，必须勾选 `tasks.md`。

### Phase 5: Review & Verify (审查与验证)
*   **动作**：代码质量审查 + 自动化/手动测试。
*   **产出**：`review-log.md` 和 `verify-log.md`。

### Phase 6: Archive & Distill (归档与提炼)
*   **动作**：合并变更，清理现场，将新知识同步到 `docs/wiki/`。

## 2. 辩证思考在流程中的强制嵌入

*   在 **Propose** 阶段，必须自问：“这个设计是否为了图快而牺牲了可扩展性？”
*   在 **Apply** 阶段，发现更好的实现方式时，必须回溯更新 `proposal.md`，禁止私自偏离设计。
*   在 **Distill** 阶段，必须总结：“这次变更中，有哪些坑是下次可以避免的？”
