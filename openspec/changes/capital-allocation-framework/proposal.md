# Proposal: Capital Allocation Framework — 资金分配框架

## Why

CIO 当前输出"减 A 到 2%，买 B 到 5%"，但没有全局资金约束和资金来源-去向配对。如果多个处方同时要求操作，可能出现：
- 资金需求总和 > 可用现金（处方之间相互打架）
- 减仓释放的资金没有被显式分配给加仓（资金流向不透明）
- 用户无法一眼看懂"卖掉谁的钱去买谁"

## Design Overview

### 核心变更

```
Before: CIO 输出独立处方，每条带 target_weight
After:  CIO 在资金约束下分配，处方输出 资金来源-去向 配对表
```

### 变更范围

1. **CIO prompt** (`cio.py`)：新增"资金分配框架"约束章节，要求输出配对表
2. **Prescription schema**：已有字段满足需求，新增 `capital_source` 字段标注资金来源

### 不涉及

- 新数据模型类（约束已在 state 中传递）
- 后端 API 变更
- 前端变更

### 方案对比

- 方案 A（Prompt only）：只在 CIO prompt 中加入资金约束要求。优点：零文件新增。缺点：LLM 可能不遵守。
- 方案 B（Validator + Prompt）：新增资金约束校验器，后处理验证处方。优点：确定性校验。缺点：多一个文件。

选择方案 A，理由：
1. 约束已在 prompt 中传递（max_single, max_industry, available_cash, total_assets）
2. 资金配对逻辑需要 LLM 判断（什么卖出、什么买入），不是机械规则
3. 可在 P3 阶段加校验器
