# 项目起源与合并思路

> 记录 tradingagents-cn 在 AI-Coding-Engine 中的定位、合并策略和演进方向

## 两个上游

| 仓库 | 定位 | 核心能力 |
|------|------|---------|
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (简称 TG) | 原版多 Agent 交易分析框架 | LangGraph 管线、多 LLM 支持、structured output、checkpoint 断点恢复、情绪预抓取、ChromaDB 记忆 |
| [hsliuping/TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN) (简称 TG-CN) | 中文增强版 | A股/港股数据(AKShare/Tushare/BaoStock)、FastAPI+Vue3 全栈 Web、MongoDB+Redis 持久化、Docker 多架构部署、中文 LLM 适配(DashScope/DeepSeek/GLM)、配置管理体系 |

## 合并策略

**以 TG-CN 为底座**，将 TG 的核心能力增量吸收：

```
TG-CN v1.0.1 (底座)
  ├── 保留：Web 全栈、中文数据源、配置体系、Docker 部署、中文文档
  ├── 吸收 TG v0.2.5：structured output、checkpoint、sentiment prefetch
  └── 独立演进：不强行对齐上游，按模块按收益人工吸收
```

**为什么以 TG-CN 为底座而非 TG：**
1. TG-CN 已有完整的产品形态（Web UI + CLI + Docker），TG 只有 CLI + Streamlit
2. 中文市场的数据源、LLM 适配、国际化工作量巨大，不可能在 TG 上重做
3. TG-CN 的配置管理和数据库体系已形成独立分叉，强行对齐成本 > 收益
4. 核心 Agent 管线（tradingagents/ 包）结构相似，增量合并可行

**吸收原则（三问决策）：**
1. 属于"核心能力"还是"本地分叉区"？ → 核心能力才吸收
2. 能否拆成独立小批次？ → 不能拆的暂缓
3. 现有测试能覆盖吗？ → 不能验证的暂缓

## 已完成的合并

### P0 核心集成 (2026-05-16)
从 TG v0.2.5 吸收三项核心能力：
- **结构化输出** — Pydantic schema + bind_structured() + 降级回退
- **Checkpoint 断点恢复** — SqliteSaver 封装，默认关闭
- **情绪预抓取** — 注册式源框架 + 东方财富 + 微信公众号

设计约束：新增不改已有数据流路径，不引入强制依赖，全部有降级路径。

### 此前已完成的吸收
- `llm_clients` 抽象层接入主链路
- 共享模型目录接入 CLI
- Provider 规范键统一（qwen/glm/openai/google/deepseek/...）
- `trading_graph.py` provider 初始化路径收口

## 不对齐的部分

以下明确不追求与 TG 上游一致：
- 中文文档体系
- Web 后端配置管理体系（MongoDB 存储）
- MongoDB/Redis 多环境隔离策略
- 中国市场数据源和中文增强功能
- 运营、部署、便携版脚本

## 在 ACE Engine 中的角色

本项目作为 `domains/tradingagents-cn` 子模块存在于 AI-Coding-Engine 中：
- 遵循 ACE 工作流（planner → applier → reviewer → archiver → retro）
- 使用 `domain.yaml` 定义服务/脚本/规范
- 知识沉淀到 `docs/wiki/`，通过 ACE retro 持续积累
- 变更管理用 OpenSpec（`openspec/changes/`）

## 后续演进方向

1. **继续按需吸收 TG 上游** — 关注 LLM 抽象、工具调用稳定性、数据流优化
2. **Web 产品能力增强** — 模拟交易、选股策略、报告导出
3. **中文市场深化** — 更多 A 股/港股数据源、中文情绪分析
4. **Agent 管线优化** — 研究深度分级、记忆系统增强
