---
name: dialectical-thinking
description: >
  Use when facing: complex decisions, architecture choices, technical tradeoffs, 
  feature design, multi-option selection, requirement analysis, API design, 
  database schema design, framework selection, library selection, technology choice,
  system design, data model design, implementation strategy, deployment approach,
  security architecture, performance optimization strategy, migration planning,
  integration pattern selection, state management approach, error handling strategy,
  testing strategy, code organization, module structure. Provides structured 
  dialectical workflow: Question assumptions, Explore alternatives, Compare tradeoffs, 
  Decide with reasoning. Offers flexible workflow that can be accepted or declined.
---

# Dialectical Thinking Skill

系统化的辩证思考工具，帮助在复杂决策中避免单一路径依赖，通过结构化的四阶段工作流（Question → Explore → Compare → Decide）实现多方案探索和理性决策。

## When to Use This Skill

主动触发此 Skill 的场景：

- **架构设计**: 系统架构、模块结构、数据模型设计
- **技术选型**: 框架选择、库选择、工具选择、语言选择
- **方案决策**: 面对多种实现路径需要选择最优方案
- **需求分析**: 需求本身存在模糊性或多种理解方式
- **权衡分析**: 明确需要分析 pros/cons 或 tradeoffs
- **API 设计**: RESTful vs GraphQL、同步 vs 异步等设计决策
- **性能优化**: 多种优化策略之间的选择
- **迁移计划**: 系统迁移、数据迁移的方案设计

## When NOT to Use This Skill

以下场景不应触发：

- **简单任务**: 代码格式化、修复 typo、变量重命名等琐碎任务
- **已有明确决策**: 用户已经决定使用某方案，只需要实现
- **单一方案问题**: 问题明显只有一个合理解决方案
- **正在实现中**: OpenSpec Apply 阶段的编码实现过程
- **快速问答**: 用户明确表示"quick question"、"just tell me"、"不要过度思考"

## Workflow

### Workflow Offer

当检测到复杂决策场景时，我会这样开场：

> 我注意到这是一个 **[复杂决策/架构设计/技术选型]** 任务。
>
> 我可以引导你通过辩证思考工作流：
> 1. **Question** - 质疑问题本身（需求是否合理？有哪些隐含假设？）
> 2. **Explore** - 探索 2-3 种方案（不同方向，暂不评判优劣）
> 3. **Compare** - 对比权衡（多维度对比表格 + 关键权衡点）
> 4. **Decide** - 给出推荐（明确推荐 + 理由 + 注意事项）
>
> 或者你希望直接讨论方案？

**你可以选择**:
- 接受工作流：我会带你走完整流程
- 直接讨论：跳过结构化流程，快速给出方案
- 部分使用：指定从某个阶段开始（如"直接 Explore"）

### Stage 1: Question - 质疑问题

**目标**: 挑战需求本身，识别隐含假设，重新定义问题

**输出格式**:
```markdown
## 质疑问题 (Question)

### 需求本身是否合理？
[分析需求的合理性，是否存在更本质的问题需要解决]

### 有哪些隐含假设？
- 假设 1: [识别出的假设]
- 假设 2: [识别出的假设]
- ...

### 问题定义是否清晰？
[如果问题定义模糊，重新定义问题]
```

**关键指引**:
- 使用第一性原理：回到问题的本质，而不是表面需求
- 识别约束条件：哪些是真实约束？哪些是自我设限？
- 挑战假设：每个"理所当然"都值得质疑

**阶段转换**:
- 完成 Question 后询问："继续探索方案（Explore）还是直接给结论？"
- 允许跳过：如果用户确认问题清晰，可直接进入 Explore

### Stage 2: Explore - 探索方案

**目标**: 生成 2-3 种不同方向的方案，暂不评判优劣

**输出格式**:
```markdown
## 探索方案 (Explore)

### 方案 A: [简短标题]
**核心思路**: [一句话描述核心理念]
**关键技术**: [使用的技术栈或模式]
**实现概要**: [高层实现策略]

### 方案 B: [简短标题]
**核心思路**: ...
**关键技术**: ...
**实现概要**: ...

### 方案 C: [简短标题] (可选)
**核心思路**: ...
**关键技术**: ...
**实现概要**: ...
```

**关键指引**:
- 确保方案真正不同：不是微调参数，而是不同的解决路径
- 中立呈现：此阶段不预设优劣，平等展示所有方案
- 覆盖光谱：从简单到复杂、从传统到创新、从保守到激进

**阶段转换**:
- 完成 Explore 后询问："继续对比分析（Compare）还是已经有倾向？"
- 允许增加方案：如果用户想到新方案，可以添加

### Stage 3: Compare - 对比分析

**目标**: 多维度对比方案，识别关键权衡点

**输出格式**:
```markdown
## 对比分析 (Compare)

| 维度           | 方案 A | 方案 B | 方案 C |
|---------------|--------|--------|--------|
| 实现复杂度     | ★★☆    | ★☆☆    | ★★★    |
| 性能          | 高     | 中     | 极高    |
| 可维护性       | 中     | 高     | 低     |
| 学习成本       | 低     | 中     | 高     |
| 扩展性        | 中     | 高     | 中     |
| 社区支持       | 强     | 强     | 弱     |

### 关键权衡点
- **权衡 1**: [描述第一个关键权衡，如"复杂度 vs 性能"]
  - 方案 A: ...
  - 方案 B: ...
  
- **权衡 2**: [描述第二个关键权衡]
  - 方案 A: ...
  - 方案 B: ...
```

**对比维度参考**:
- **技术维度**: 实现复杂度、性能、可靠性、安全性
- **工程维度**: 可维护性、可测试性、可扩展性
- **团队维度**: 学习成本、开发效率、招聘难度
- **生态维度**: 社区支持、文档质量、库生态

**阶段转换**:
- 完成 Compare 后询问："继续决策推荐（Decide）还是你已经有决定？"

### Stage 4: Decide - 决策推荐

**目标**: 明确推荐一个方案，给出理由和注意事项

**输出格式**:
```markdown
## 决策推荐 (Decide)

### 推荐方案: 方案 [X]

**推荐理由**:
1. [具体理由 1，结合项目上下文]
2. [具体理由 2，结合项目上下文]
3. [具体理由 3，如果有]

**注意事项**:
- [注意点 1: 实施时需要注意的风险或细节]
- [注意点 2: 可能遇到的坑]
- [注意点 3: 需要额外关注的点]

**不推荐的原因** (其他方案):
- **方案 Y**: [为什么不推荐的简短说明]
- **方案 Z**: [为什么不推荐的简短说明]

**后续行动**:
- [建议的下一步，如"创建技术设计文档"、"进行 POC 验证"等]
```

**关键指引**:
- 明确推荐：不能模棱两可，必须选定一个方案
- 有理有据：推荐理由必须具体，结合项目上下文
- 诚实风险：列出潜在风险，不夸大优点
- 尊重其他方案：解释为什么不选，而不是贬低

## Workflow Navigation

### 灵活导航

用户可以随时：
- **跳过阶段**: "跳过 Question，直接 Explore"
- **返回阶段**: "回到 Explore，我想添加一个方案"
- **中途退出**: "直接给我结论" → 基于当前已有信息提供总结
- **暂停继续**: "先到这里" → 保存当前进度，随时可继续

### 手动触发

即使自动触发没有生效，用户也可以手动调用：
- "使用辩证思考"
- "辩证分析一下"
- "帮我走一遍辩证流程"

## Progressive Disclosure - 需要更多指引？

如果你需要更深入的指导：

- **辩证原则库** (`references/principles.md`): 
  - 第一性原理、逆向思维、魔鬼代言人等核心思维方法
  - 适合在 **Question 阶段** 需要更多质疑技巧时查看

- **思考模式库** (`references/patterns.md`):
  - SWOT 分析、五个为什么、决策矩阵等结构化模板
  - 适合在 **Explore 和 Compare 阶段** 需要分析框架时查看

- **实战案例库** (`references/examples.md`):
  - 真实的 ACE Engine 设计决策案例（完整四阶段流程）
  - 适合在 **任何阶段** 需要参考示例时查看

这些参考资料是可选的，默认不加载以节省上下文。只有在你需要时才查看。

## Integration with OpenSpec

此 Skill 与 OpenSpec 工作流自然集成：

- **Explore 阶段**: 最适合使用辩证思考，深入分析问题和方案
- **Plan 阶段**: 适合在确定实现策略时使用
- **Apply 阶段**: 不应主动触发，避免打断编码流程

## Examples

### 快速示例: 缓存方案选择

**Question**:
- 需求合理性: ✓ 确实需要缓存以提升性能
- 隐含假设: 假设数据一致性要求不严格、假设缓存失效可接受
- 问题重定义: "选择适合当前规模（10K 用户）的缓存方案，优先考虑简单性"

**Explore**:
- 方案 A: Redis (独立服务)
- 方案 B: In-memory (应用内存)
- 方案 C: SQLite (本地文件)

**Compare**:
| 维度 | Redis | In-memory | SQLite |
|------|-------|-----------|--------|
| 复杂度 | ★★★ | ★☆☆ | ★★☆ |
| 性能 | 极高 | 极高 | 高 |
| 持久化 | 支持 | 不支持 | 支持 |
| 部署成本 | 高 | 低 | 低 |

**Decide**:
推荐 **In-memory**
- 理由: 当前规模小，部署简单，性能足够
- 注意: 重启后缓存丢失，需要预热策略
- 不推荐 Redis: 当前阶段过度设计

---

**这个 Skill 的价值**: 避免 AI 的"执行者模式"，在复杂决策时提供结构化思考，确保多方案探索和理性权衡。
