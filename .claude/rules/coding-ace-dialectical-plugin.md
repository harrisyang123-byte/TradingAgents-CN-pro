# ACE 辩证思考插件 (Dialectical Thinking Plugin)

> **触发条件**: 在执行 `/opsx:propose` 或手动编写 `proposal.md` 时。

## 1. 核心契约 (The Contract)
AI 必须在 `proposal.md` 的 `## Why` 章节之后，插入一个隐藏或显式的 `<!-- Dialectical Analysis -->` 块。

## 2. 思考清单 (Checklist)
*   **多路径对比**: 方案 A (保守) vs 方案 B (创新) 的权衡。
*   **取长补短**: 记录参考了哪些 upstream 或 reference 工程的亮点。
*   **风险对冲**: 识别本次变更最可能失败的点，并给出预备方案。

## 3. 验证要求
每一个新 Capability 必须至少包含一个 **"Edge Case" (边缘案例)** 的 Scenario。
