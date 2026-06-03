## Context

当前 Tier 2 使用 LangGraph 四层管线（12 Agent + 辩论循环），存在 msg_clear 导致层间上下文断裂、各 Agent 独立看不到跨层矛盾、Tier1 匹配率 25% 等问题。

本变更在 `feature/claude-code-advisor` 新分支上构建 Python 编排 + 9 个子 Agent 混合架构。原 LangGraph 代码保留在 `fix/fund-akshare-api-error` 分支不动。数据工具层全部复用（market_tools, pe_percentile, ExposureService 等）。

## Goals / Non-Goals

**Goals**:
- 子 Agent 有完整上下文——不通过 msg_clear 断裂
- 交叉验证能检出至少 1 个 Tier1 矛盾
- 处方 100% 覆盖持仓，含敞口诊断 + 资金分配
- 单次分析 ≤ 5min
- 前端零改动，MongoDB 写入格式兼容

**Non-Goals**:
- 不修改 LangGraph 原代码
- 不做组合回测/因子暴露/相关性矩阵（v4）
- 不修改前端代码

## Decisions

### D1: JSON 文件总线 vs msg_clear 链

**选择**: JSON 文件总线。每个子 Agent 读前面全部 `/tmp/claude_advisor/step*.json` → 推理 → 写自己的 JSON。

**理由**: 消除 LangGraph msg_clear 导致的上下文断裂。

**替代方案**: 修 LangGraph 的 state 注入逻辑。工作量更大（6 个文件），且仍受 LangGraph StateGraph schema 约束。

### D2: 子 Agent = 单次 LLM 调用 vs Workflow agent()

**选择**: Python 直接调 `llm.invoke()`。每个子 Agent = 1 次 LLM 调用，有独立 system prompt。

**理由**: Workflow `agent()` 在当前版本有序列化 bug（长 prompt → `[object Object]`）。Python 直接调用无此问题。

### D3: L2 反向者 + 裁判移除

**选择**: 移除。反方向题由 Scout 自带 `top_risks` 字段 + 交叉验证规则引擎覆盖。裁判由 6 维评分确定性映射表覆盖。

**理由**: 反向者和裁判与 Scout 共享同一套工具和数据源——没有信息不对称。证伪方式：E2E 对比两版输出。

### D4: L3 侦察兵移除

**选择**: 移除。组合缺口由 "L1 低配行业 + 策略师集中度反向计算" 覆盖。

**理由**: 侦察兵没有工具调用能力，只看持仓+L2，不读 Tier1。缺口信息已在 L1 和 L3 中散布。

### D5: 情绪数据 = 每个 Agent 的直接输入，而非新 Agent

**选择**: 市场温度计作为数据收集层的一部分，输出 `market_temperature.json`，每个已有 Agent 消费该文件。

**理由**: 新加一个 "新闻分析员" Agent 会导致信息割裂——L1 看不到它的结论，它看不到 L1 的行业判断。

## Risks / Trade-offs

- **[风险] AKShare 情绪数据采集中断** → 在 `market_temperature.json` 中标记 "数据不可用"，Agent 回归纯基本面判断
- **[风险] 9 个子 Agent 的串行 LLM 调用总耗时超 5min** → 如果 L2 Scout 的工具调用过多(6 工具 × 多次往返)，限制调用上限为 3 轮
- **[风险] JSON 文件写冲突（Agent 同时读同一文件）** → 所有 Agent 串行执行，不存在并发写

## Migration Plan

1. 在 `feature/claude-code-advisor` 分支上开发 `cli/claude_advisor.py`
2. E2E 验证通过后，向前端展示效果
3. 用户确认后，可选：替换前端按钮的触发方式为 CLI（后续）
4. 不删除 LangGraph 代码，双线共存
5. 回滚：切回 `fix/fund-akshare-api-error` 分支即可

## Open Questions

1. 子 Agent 的 LLM 模型选择：用 deepseek-v4-flash 还是 deepseek-v4-pro？前者更快但评分精度可能略低于后者
2. 交叉验证规则是否应扩展为 LLM 辅助（而非纯规则引擎）？当前规则引擎受限在预先定义的检测类型，LLM 可以发现未知的异常模式
3. 基金穿透数据采集：AKShare SSL 问题是否有稳定解决方案？
